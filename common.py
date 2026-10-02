"""knit. 공통 코드 (여러 화면이 같이 쓰는 것들)
- 디자인(CSS), 안전 필터, 지역 목록, 데이터베이스, 닉네임 입력
"""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from sqlalchemy import create_engine, text

# =====================================================================
# 1. 공통: 디자인(CSS) / 안전 필터 / 지역
# =====================================================================

REGIONS = {  # 이름: (위도, 경도, 줌)
    "서울": (37.5665, 126.9780, 11), "부산": (35.1796, 129.0756, 11),
    "대구": (35.8714, 128.6014, 11), "인천": (37.4563, 126.7052, 11),
    "광주": (35.1595, 126.8526, 11), "대전": (36.3504, 127.3845, 11),
    "울산": (35.5384, 129.3114, 11), "세종": (36.4800, 127.2890, 11),
    "경기": (37.4138, 127.5183, 9), "강원": (37.8228, 128.1555, 8),
    "충북": (36.6357, 127.4917, 9), "충남": (36.5184, 126.8000, 9),
    "전북": (35.7175, 127.1530, 9), "전남": (34.8161, 126.4629, 8),
    "경북": (36.4919, 128.8889, 8), "경남": (35.4606, 128.2132, 9),
    "제주": (33.4996, 126.5312, 10),
}

STITCH = ("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='28'%3E"
          "%3Cpath d='M4 3 L12 23 L20 3' fill='none' stroke='%23B5502E' "
          "stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap');
:root { --ink:#1F1B18; --sub:#7A736C; --line:#E7E2DB; --bg:#FAF8F5; --panel:#F3EFE9; --acc:#B5502E; --tint:#F7E8E0; }
html, body, .stApp, .stMarkdown, input, textarea, button { font-family:'Noto Sans KR',system-ui,sans-serif; }
.stApp { background:var(--bg); color:var(--ink); }
h1 { font-family:'Noto Serif KR',serif !important; font-weight:700 !important; font-size:2rem !important;
  letter-spacing:-.02em; color:var(--ink) !important; }
h2,h3,h4 { font-family:'Noto Serif KR',serif !important; font-weight:600 !important; letter-spacing:-.01em; color:var(--ink) !important; }
[data-testid="stSidebar"] { background:var(--panel); border-right:1px solid var(--line); }
.wordmark, .eyebrow { font-family:'Noto Serif KR',serif; font-weight:700; letter-spacing:-.04em; line-height:1; }
.wordmark { font-size:30px; }
.wordmark.xl { font-size:72px; }
.eyebrow { font-size:15px; color:var(--sub); margin-bottom:-4px; }
.wordmark span, .eyebrow span { color:var(--acc); }
.hero { padding:24px 0 6px; }
.tagline { font-family:'Noto Serif KR',serif; font-size:26px; font-weight:600; margin:14px 0 6px; letter-spacing:-.01em; }
.lede { color:var(--sub); max-width:560px; margin:0 0 12px; }
.stitch { height:12px; background:url("__STITCH__") repeat-x; background-size:auto 12px; margin:14px 0 22px; }
.stButton>button, .stFormSubmitButton>button { border-radius:10px; border:1px solid var(--ink); background:var(--ink);
  color:#fff; font-weight:500; padding:.45rem 1.1rem; }
.stButton>button:hover, .stFormSubmitButton>button:hover { background:var(--acc); border-color:var(--acc); color:#fff; }
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"]>div, .stDateInput input {
  border-radius:10px !important; background:#fff; }
.stTabs [data-baseweb="tab"] { font-weight:500; }
.knit-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 20px; margin:6px 0 10px; }
.knit-card h3 { margin:4px 0 6px; font-size:1.15rem; }
.knit-card p { margin:4px 0; word-break:break-word; color:#3a3430; }
.num { font-family:'Noto Serif KR',serif; color:var(--acc); font-size:13px; font-weight:700; letter-spacing:.08em; }
.tag { display:inline-block; background:var(--panel); color:var(--sub); border-radius:6px; padding:1px 9px;
  font-size:12px; margin:0 4px 4px 0; }
.tag.k { background:var(--tint); color:var(--acc); font-weight:500; }
.safe-box { background:var(--panel); border-left:3px solid var(--acc); border-radius:8px; padding:10px 16px; font-size:14px; }
.cmt { background:#fff; border:1px solid var(--line); border-radius:10px; padding:6px 12px; margin:6px 0; font-size:14px; }
.muted { color:var(--sub); font-size:12px; }
</style>
""".replace("__STITCH__", STITCH)


def secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


def esc(s):
    """사용자 입력을 HTML에 넣기 전에 반드시 통과시키는 함수."""
    return html.escape(str(s or "")).replace("\n", "<br>")


_BLOCK = [
    (r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}", "전화번호"),
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "이메일"),
    (r"https?://|www\.|\.(com|kr|net|me)\b", "링크"),
    (r"카톡|카카오\s?톡|오픈\s?채팅|인스타|텔레그램|\bdm\b|디엠", "외부 연락처/SNS"),
]


def check_text(*texts):
    """개인정보·외부연락처가 있으면 안내 문구를 돌려주고, 괜찮으면 None."""
    for t in texts:
        for pat, label in _BLOCK:
            if re.search(pat, t or "", re.I):
                return f"{label}는 안전을 위해 쓸 수 없어요. 댓글로 이야기해요!"
    return None


def setup():
    """모든 화면 파일에서 '가장 먼저' 한 번 부르는 함수 (페이지 설정 + 디자인 + 닉네임)."""
    st.set_page_config(page_title="knit.", page_icon="🧶", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.session_state.setdefault("nickname", "")
    with st.sidebar:
        st.markdown("---")
        st.markdown("**닉네임**")
        n = st.text_input("닉네임", value=st.session_state.nickname, max_chars=12, key="nick_w",
                          placeholder="예: 뜨개곰", help="실명·학교 이름은 쓰지 마세요!").strip()
        # 닉네임에도 연락처·링크 필터 적용
        if check_text(n):
            st.warning("닉네임에는 전화번호·링크·SNS 아이디를 쓸 수 없어요.")
            n = ""
        st.session_state.nickname = n
        st.markdown("---")


def header(title, sub=""):
    st.markdown(f"<div class='eyebrow'>knit<span>.</span></div><h1>{esc(title)}</h1>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<span class='muted' style='font-size:15px'>{esc(sub)}</span>", unsafe_allow_html=True)
    st.markdown("<div class='stitch'></div>", unsafe_allow_html=True)


# =====================================================================
# 2. 데이터베이스 (DATABASE_URL 있으면 Postgres, 없으면 SQLite)
#    ※ Streamlit Cloud에서 SQLite는 재시작하면 데이터가 사라져요.
#      배포할 때는 Supabase/Neon 같은 Postgres 주소를 DATABASE_URL로 넣으세요.
# =====================================================================

KINDS = ["모임", "수다", "질문", "작품"]


@st.cache_resource
def engine():
    url = secret("DATABASE_URL", "sqlite:///knit.db")
    if url.startswith("postgres://"):  # SQLAlchemy는 postgresql:// 만 인식
        url = url.replace("postgres://", "postgresql://", 1)
    eng = create_engine(url, pool_pre_ping=True)
    pk = "SERIAL PRIMARY KEY" if eng.dialect.name == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with eng.begin() as c:
        c.execute(text(f"""CREATE TABLE IF NOT EXISTS posts (
            id {pk}, kind TEXT, title TEXT, body TEXT, nick TEXT, region TEXT,
            place TEXT, meet_date TEXT, created TEXT, reports INTEGER DEFAULT 0)"""))
        c.execute(text(f"""CREATE TABLE IF NOT EXISTS comments (
            id {pk}, post_id INTEGER, nick TEXT, body TEXT, created TEXT)"""))
    return eng


def now():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")


def q(sql, **p):
    with engine().connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), p)]


def ex(sql, **p):
    with engine().begin() as c:
        c.execute(text(sql), p)
