
import os
import re
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, Text, DateTime, UniqueConstraint,
    select, text
)

KST = ZoneInfo("Asia/Seoul")

# -------------------------
# 기본 설정
# -------------------------

REGIONS = [
    "전체", "서울", "경기", "인천", "강원",
    "충청", "전라", "경상", "제주", "온라인"
]

KINDS = ["모임", "수다", "질문", "작품"]

COLORS = {
    "bg": "#FAF8F5",
    "ink": "#1F1B18",
    "accent": "#B5502E",
    "panel": "#F3EFE9",
    "muted": "#7A736C",
    "line": "#E7E2DB",
    "white": "#FFFFFF",
}

LEVELS = [
    (0, "새싹 뜨개러", "대나무 바늘"),
    (100, "수습 뜨개러", "나무 바늘"),
    (300, "솜씨 좋은 뜨개러", "알루미늄 바늘"),
    (700, "뜨개 장인", "은빛 바늘"),
    (1500, "전설의 뜨개러", "황금 바늘"),
]

def now():
    return datetime.now(KST).replace(tzinfo=None)

def secret(name, default=None):
    try:
        value = st.secrets.get(name, default)
        if value:
            return value
    except Exception:
        pass
    return os.environ.get(name, default)

def esc(value):
    """HTML에 안전하게 표시하기 위한 문자열 변환."""
    return html.escape(str(value or ""), quote=True)

# -------------------------
# 데이터베이스
# -------------------------

@st.cache_resource
def get_engine():
    url = secret("DATABASE_URL", "sqlite:///knit.db")

    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}

    return create_engine(url, **options)

engine = get_engine()
metadata = MetaData()

posts = Table(
    "posts", metadata,
    Column("id", Integer, primary_key=True),
    Column("nick", String(40), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("region", String(30), nullable=False),
    Column("title", String(120), nullable=False),
    Column("body", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("reports", Integer, nullable=False, default=0),
)

comments = Table(
    "comments", metadata,
    Column("id", Integer, primary_key=True),
    Column("post_id", Integer, nullable=False),
    Column("nick", String(40), nullable=False),
    Column("body", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

records = Table(
    "records", metadata,
    Column("id", Integer, primary_key=True),
    Column("nick", String(40), nullable=False),
    Column("record_date", String(10), nullable=False),
    Column("project", String(80), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

rewards = Table(
    "rewards", metadata,
    Column("id", Integer, primary_key=True),
    Column("nick", String(40), nullable=False),
    Column("reward_key", String(150), nullable=False),
    Column("points", Integer, nullable=False),
    Column("reason", String(100), nullable=False),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint("nick", "reward_key", name="uq_reward_nick_key"),
)

reports = Table(
    "post_reports", metadata,
    Column("id", Integer, primary_key=True),
    Column("post_id", Integer, nullable=False),
    Column("reporter", String(40), nullable=False),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint("post_id", "reporter", name="uq_report_post_reporter"),
)

with engine.begin() as conn:
    metadata.create_all(conn)

    # 기존 DB에 reports 열이 없을 때를 위한 간단한 SQLite 이전 처리
    if engine.dialect.name == "sqlite":
        cols = conn.execute(text("PRAGMA table_info(posts)")).fetchall()
        if cols and "reports" not in [row[1] for row in cols]:
            conn.execute(
                text("ALTER TABLE posts ADD COLUMN reports INTEGER NOT NULL DEFAULT 0")
            )

def q(sql, params=None):
    """SQL 조회 결과를 dict 목록으로 반환."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row) for row in result.mappings().all()]

def ex(sql, params=None):
    """SQL 실행."""
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount

# -------------------------
# 포인트 및 레벨
# -------------------------

def get_points(nick):
    row = q(
        "SELECT COALESCE(SUM(points), 0) AS total "
        "FROM rewards WHERE nick = :nick",
        {"nick": nick},
    )
    return int(row[0]["total"]) if row else 0

def award_points(nick, reward_key, points, reason):
    """
    같은 닉네임과 reward_key 조합에는 한 번만 지급.
    중복 제출로 인한 포인트 중복 지급을 방지한다.
    """
    if not nick or points <= 0:
        return False

    try:
        with engine.begin() as conn:
            conn.execute(
                rewards.insert().values(
                    nick=nick,
                    reward_key=reward_key,
                    points=points,
                    reason=reason,
                    created_at=now(),
                )
            )
        return True
    except Exception:
        # 유일성 제약 조건에 걸린 중복 지급 등
        return False

def get_level(points):
    current = LEVELS[0]
    for level in LEVELS:
        if points >= level[0]:
            current = level
    return current

def get_next_level(points):
    for level in LEVELS:
        if points < level[0]:
            return level
    return None

def get_user_stats(nick):
    points = get_points(nick)
    level = get_level(points)
    next_level = get_next_level(points)

    if next_level:
        progress = (points - level[0]) / (next_level[0] - level[0])
        remaining = next_level[0] - points
    else:
        progress = 1.0
        remaining = 0

    return {
        "points": points,
        "level": level[1],
        "item": level[2],
        "progress": max(0.0, min(1.0, progress)),
        "remaining": remaining,
        "next_level": next_level,
    }

# -------------------------
# 입력값 검사
# -------------------------

_BLOCK = [
    r"\b\d{2,4}[- ]?\d{3,4}[- ]?\d{4}\b",  # 전화번호
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",  # 이메일
    r"https?://\S+",                         # URL
    r"www\.\S+",                             # URL
]

def check_text(value, max_length=2000):
    value = str(value or "").strip()

    if not value:
        return False, "내용을 입력해 줘."

    if len(value) > max_length:
        return False, f"{max_length}자 이하로 작성해 줘."

    for pattern in _BLOCK:
        if re.search(pattern, value, re.IGNORECASE):
            return False, "개인 연락처나 외부 링크는 입력할 수 없어."

    return True, value

# -------------------------
# 공통 디자인
# -------------------------

def setup():
    st.set_page_config(
        page_title="knit.",
        page_icon="🧶",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap');

        :root {
            --bg: #FAF8F5;
            --ink: #1F1B18;
            --accent: #B5502E;
            --panel: #F3EFE9;
            --muted: #7A736C;
            --line: #E7E2DB;
        }

        .stApp {
            background: var(--bg);
            color: var(--ink);
            font-family: 'Noto Sans KR', sans-serif;
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: -0.04em;
        }

        .knit-kicker {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            text-transform: uppercase;
        }

        .knit-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 22px;
            margin-bottom: 12px;
        }

        .knit-muted {
            color: var(--muted);
            font-size: 0.9rem;
        }

        .stButton > button {
            border-radius: 12px;
            border: 1px solid var(--line);
            min-height: 42px;
        }

        .stButton > button[kind="primary"] {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        [data-testid="stSidebar"] {
            background: #F3EFE9;
            border-right: 1px solid #E7E2DB;
        }

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px;
        }

        .stProgress > div > div > div > div {
            background-color: var(--accent);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "nick" not in st.session_state:
        st.session_state.nick = "뜨개러"

    with st.sidebar:
        st.markdown("## 🧶 knit.")
        st.caption("나만의 뜨개 기록 공간")
        nickname = st.text_input(
            "닉네임",
            value=st.session_state.nick,
            max_chars=20,
            key="nickname_input",
        ).strip()

        if nickname:
            st.session_state.nick = nickname

        st.divider()
        st.caption("활동을 기록하고 포인트를 모아 봐!")

def header(title, subtitle=""):
    st.markdown('<div class="knit-kicker">KNIT. STUDIO</div>', unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()
