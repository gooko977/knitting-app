"""knit. - 뜨개 AI: 도안 생성 + 내 게이지 입력 + 뜨개샵 지도 + 뜨개모임 (한 파일 버전)
실행: streamlit run app.py
"""
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
import folium
import requests
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text
from streamlit_folium import st_folium

st.set_page_config(page_title="knit.", page_icon="🧶", layout="wide")

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


NAV = ["홈", "AI 도안", "뜨개샵 지도", "뜨개모임"]


def setup():
    st.markdown(CSS, unsafe_allow_html=True)
    st.session_state.setdefault("nickname", "")
    st.session_state.setdefault("nav", NAV[0])
    with st.sidebar:
        st.markdown("<div class='wordmark'>knit<span>.</span></div><div class='muted' style='margin-top:4px'>뜨개를 위한 AI</div>", unsafe_allow_html=True)
        st.radio("메뉴", NAV, key="nav", label_visibility="collapsed")
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
        c.execute(text(f"""CREATE TABLE IF NOT EXISTS shops (
            id {pk}, name TEXT, region TEXT, address TEXT, lat DOUBLE PRECISION,
            lon DOUBLE PRECISION, note TEXT, nick TEXT, created TEXT)"""))
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


# =====================================================================
# 3. 홈
# =====================================================================
def go(label):
    st.session_state.nav = label


def page_home():
    st.markdown("""
<div class="hero">
  <div class="wordmark xl">knit<span>.</span></div>
  <div class="tagline">말로 설명하면, 도안이 됩니다.</div>
  <p class="lede">만들고 싶은 뜨개를 설명하면 AI가 완성 이미지와 도안, 필요한 바늘 호수까지 정리해 드려요. 내 손 게이지를 넣으면 코수와 단수도 다시 계산해 줘요.</p>
  <span class="tag k">코바늘</span><span class="tag k">대바늘</span><span class="tag">호수 추천</span><span class="tag">케이블 길이</span><span class="tag">게이지 10×10cm</span>
</div>
<div class="stitch"></div>""", unsafe_allow_html=True)
    items = [("01", "AI 도안", "아이디어를 말하면 완성 이미지와 단계별 도안을 만들어 줘요."),
             ("02", "뜨개샵 지도", "전국의 털실가게와 뜨개 공방을 지도에서 찾아요."),
             ("03", "뜨개모임", "함께 뜰 사람을 찾고, 질문하고, 작품을 나눠요.")]
    for col, (n, t, d), label in zip(st.columns(3), items, NAV[1:]):
        with col:
            st.markdown(f'<div class="knit-card"><div class="num">{n}</div><h3>{t}</h3><p>{d}</p></div>',
                        unsafe_allow_html=True)
            st.button(f"{t} 열기", key=f"go_{t}", on_click=go, args=(label,))


# =====================================================================
# 4. 도안 챗봇 (+ 내 게이지 입력)
# =====================================================================

MODEL = "claude-sonnet-5-5"
MAX_CALLS = 15  # 한 세션에서 도안을 만들 수 있는 최대 횟수 (API 비용 보호)

GUIDE = """한국 뜨개 호수 참고표:
코바늘: 2/0호=2.0mm, 3/0호=2.3mm, 4/0호=2.5mm, 5/0호=3.0mm, 6/0호=3.5mm, 7/0호=4.0mm, 8/0호=5.0mm, 10/0호=6.0mm
대바늘: 0호=2.1mm, 1호=2.4mm, 2호=2.7mm, 3호=3.0mm, 4호=3.3mm, 5호=3.6mm, 6호=3.9mm, 7호=4.2mm, 8호=4.5mm, 10호=5.1mm, 12호=5.7mm, 15호=6.9mm"""


@st.cache_resource
def get_client():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def build_system(tool, level, out, gauge=None):
    crochet = tool == "코바늘"
    want = {"이미지+도안": "이미지와 도안", "이미지만": "이미지만", "도안만": "도안만"}[out]
    svg_rule = (
        "빈 문자열"
        if out == "도안만"
        else '완성된 모습을 깔끔한 플랫 일러스트로 그린 SVG 문자열. <svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">로 시작, '
        "둥근 도형과 점선 스티치로 실 질감 표현, script/image 금지, 3KB 이하"
    )
    # 케이블/바늘 길이는 JSON에서도 맨 마지막(svg 바로 앞)에 둔다
    cable = "" if crochet else '  "cable": "줄바늘이면 케이블 길이(예: 80cm), 막대바늘이면 막대바늘 길이를 작품에 맞게 추천",\n'
    tool_ex = "코바늘 호수 (예: 5/0호 (3.0mm))" if crochet else "대바늘 호수 (예: 5호 (3.6mm))"
    stitches = "사슬, 짧은뜨기, 긴뜨기 등" if crochet else "겉뜨기, 안뜨기, 코잡기, 코막음 등"

    if gauge:
        extra = ""
        if gauge.get("yarn"):
            extra += f", 사용할 실: {gauge['yarn']}"
        if gauge.get("needle"):
            extra += f", 스와치를 뜬 바늘: {gauge['needle']}"
        gauge_rule = (
            f"\n[사용자 게이지] 사용자가 직접 뜬 10cm x 10cm 스와치 결과: 가로 {gauge['st']}코 x 세로 {gauge['rows']}단{extra}.\n"
            "이 게이지를 최우선 기준으로 삼아 도안의 모든 코수·단수를 다시 계산해.\n"
            "- 코수 = 가로 cm x (가로 코수 / 10), 단수 = 세로 cm x (세로 단수 / 10)\n"
            "- 무늬 반복 단위가 있으면 가장 가까운 배수로 맞춰.\n"
            '- "gauge" 필드에는 사용자가 입력한 값을 그대로 쓰고, 바늘 호수가 이 실과 게이지에 어울리는지 tip에 한 문장으로 알려줘.\n'
        )
    else:
        gauge_rule = "\n게이지는 일반적인 값으로 추정하고, 사용자가 실을 정하면 10cm x 10cm 스와치를 떠서 게이지를 알려달라고 tip에서 권해줘.\n"

    return f"""너는 친절한 한국어 뜨개질 도안 선생님이야. 사용자는 뜨개질을 좋아하는 고등학생이야.
선택 옵션: 바늘={tool}, 난이도={level}, 결과물={want}.
{GUIDE}
{gauge_rule}
반드시 JSON 객체 하나만 출력해. 코드펜스나 설명 문장은 금지. 형식:
{{
  "reply": "짧은 한마디",
  "title": "작품 이름",
  "size": "완성 크기",
  "yarn": "추천 실(굵기·소재·색·대략 g)",
  "tool": "{tool_ex}",
  "gauge": "10cm 기준 코수 x 단수",
  "other": "필요한 부자재",
  "steps": ["도안 6~12단계. 코수/단수를 구체적으로 ({stitches})"],
  "tip": "초보를 위한 팁 1~2문장",
{cable}  "svg": "{svg_rule}"
}}"""


def clean_svg(code):
    """SVG에서 위험한 태그/속성 제거."""
    try:
        code = re.sub(r"^<\?xml[^>]*\?>", "", code.strip())
        root = ET.fromstring(code)
    except ET.ParseError:
        return ""
    bad = {"script", "foreignobject", "image", "use", "a"}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split("}")[-1].lower() in bad:
                parent.remove(child)
    for el in root.iter():
        for k in list(el.attrib):
            if k.lower().startswith("on") or "javascript:" in el.attrib[k].lower():
                del el.attrib[k]
    root.set("viewBox", "0 0 300 300")
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.tostring(root, encoding="unicode")


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def ask(messages, system):
    resp = get_client().messages.create(
        model=MODEL, max_tokens=5000, system=system, messages=messages
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def show_result(r, tool, out):
    st.subheader(r.get("title", "작품"))
    svg = clean_svg(r.get("svg", "")) if r.get("svg") else ""
    if svg:
        components.html(
            f'<div style="background:#F3EFE9;border:1px solid #E7E2DB;border-radius:12px;padding:8px;text-align:center">'
            f'<div style="max-width:340px;margin:auto">{svg}</div></div>',
            height=360,
        )
    st.markdown("**준비물**")
    cols = st.columns(2)
    items = [
        ("사이즈", r.get("size")),
        ("실", r.get("yarn")),
        ("코바늘 호수" if tool == "코바늘" else "대바늘 호수", r.get("tool")),
        ("게이지 (10cm 기준)", r.get("gauge")),
        ("부자재", r.get("other")),
    ]
    for i, it in enumerate([x for x in items if x and x[1]]):
        cols[i % 2].info(f"**{it[0]}**\n\n{it[1]}")
    if r.get("steps"):
        st.markdown("**도안**" if out != "이미지만" else "**만드는 순서 요약**")
        for i, s in enumerate(r["steps"], 1):
            st.markdown(f"{i}. {s}")
    if r.get("tip"):
        st.caption(f"팁 · {r['tip']}")
    # 케이블/바늘 길이는 맨 마지막에 알려준다
    if tool == "대바늘" and r.get("cable"):
        st.info(f"**케이블/바늘 길이**\n\n{r['cable']}")
    st.caption("※ AI가 만든 그림과 도안이라 실제와 다를 수 있어요. 작은 조각으로 게이지를 먼저 떠보세요!")


def generate(user_text, tool, level, out):
    """사용자 메시지를 기록하고 도안을 만들어 화면과 대화 기록에 추가."""
    chat = st.session_state.chat
    if st.session_state.n_calls >= MAX_CALLS:
        st.warning("오늘은 여기까지! 도안 만들기 횟수를 다 썼어요. 나중에 다시 만들어 봐요.")
        return
    st.session_state.n_calls += 1

    chat.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    # API에는 최근 대화만 전달 (이전 도안은 핵심 정보만 요약)
    api_msgs = []
    for m in chat[-7:]:
        if m["role"] == "user":
            api_msgs.append({"role": "user", "content": m["content"]})
        else:
            r = m["result"]
            summary = json.dumps(
                {k: r.get(k) for k in ("title", "size", "yarn", "tool", "gauge", "steps")}, ensure_ascii=False
            )
            api_msgs.append({"role": "assistant", "content": summary})
    while api_msgs and api_msgs[0]["role"] == "assistant":
        api_msgs.pop(0)

    system = build_system(tool, level, out, st.session_state.get("gauge"))
    with st.chat_message("assistant"):
        result, err = None, None
        with st.spinner("도안을 만드는 중..."):
            for _ in range(2):  # JSON이 깨지면 한 번 더 시도
                try:
                    result = parse_json(ask(api_msgs, system))
                    break
                except Exception as e:
                    err = e
        if result is None:
            st.error("결과를 만들지 못했어요. 잠시 후 다시 시도해 주세요.")
            if secret("DEBUG"):
                st.exception(err)
            chat.pop()  # 실패한 질문은 기록에서 뺀다
            return
        st.write(result.get("reply", ""))
        show_result(result, tool, out)
    chat.append({"role": "assistant", "content": "", "result": result, "tool": tool, "out": out})


def gauge_panel():
    """마지막 도안 아래에 10cm x 10cm 게이지 입력 칸을 보여준다."""
    chat = st.session_state.chat
    if not chat or chat[-1]["role"] != "assistant":
        return
    last = chat[-1]["result"]
    g = st.session_state.get("gauge")
    n = len(chat)
    label = ("내 게이지 넣기 (10cm × 10cm)" if not g
             else f"내 게이지: 가로 {g['st']}코 × 세로 {g['rows']}단 (수정하기)")
    with st.expander(label, expanded=False):
        st.caption("실이 정해졌다면, 그 실과 바늘로 10cm × 10cm 정도 떠 보세요. "
                   "가로로 몇 코, 세로로 몇 단인지 세어서 적으면 도안의 코수·단수를 내 손 게이지에 맞춰 다시 계산해요.")
        with st.form(f"gauge_form_{n}"):
            yarn = st.text_input("사용할 실", value=((g or {}).get("yarn") or last.get("yarn") or "")[:100],
                                 max_chars=100, key=f"g_yarn_{n}")
            needle = st.text_input("스와치를 뜬 바늘 (선택)", value=(g or {}).get("needle", ""),
                                   max_chars=30, placeholder="예: 5/0호 또는 대바늘 5호", key=f"g_needle_{n}")
            c1, c2 = st.columns(2)
            stitches = c1.number_input("가로 10cm 안의 코수", min_value=4, max_value=60,
                                       value=(g or {}).get("st", 18), step=1, key=f"g_st_{n}")
            rows = c2.number_input("세로 10cm 안의 단수", min_value=4, max_value=80,
                                   value=(g or {}).get("rows", 24), step=1, key=f"g_rows_{n}")
            if st.form_submit_button("이 게이지로 도안 다시 계산"):
                msg = check_text(yarn, needle)
                if msg:
                    st.warning(msg)
                else:
                    st.session_state.gauge = {"yarn": yarn.strip(), "needle": needle.strip(),
                                              "st": int(stitches), "rows": int(rows)}
                    who = f"실은 {yarn.strip()}(으)로 정했어. " if yarn.strip() else ""
                    st.session_state.pending = (
                        f"{who}10cm × 10cm 스와치 게이지가 가로 {int(stitches)}코, 세로 {int(rows)}단이야. "
                        "이 게이지에 맞게 코수와 단수를 다시 계산해서 도안을 고쳐줘."
                    )
                    st.rerun()


def page_chat():
    header("AI 도안", "만들고 싶은 걸 말해주면 완성 이미지와 도안을 그려줄게요!")
    with st.sidebar:
        st.header("옵션")
        tool = st.radio("바늘 종류", ["코바늘", "대바늘"], horizontal=True)
        out = st.radio("결과물", ["이미지+도안", "이미지만", "도안만"])
        level = st.select_slider("난이도", ["초보", "중급", "고급"])
        g = st.session_state.get("gauge")
        if g:
            st.caption(f"적용 중인 게이지: 가로 {g['st']}코 × 세로 {g['rows']}단 (10cm)")
            if st.button("게이지 해제"):
                st.session_state.pop("gauge", None)
                st.rerun()
        if st.button("대화 초기화"):
            for k in ("chat", "gauge", "pending"):
                st.session_state.pop(k, None)
            st.rerun()

    st.session_state.setdefault("chat", [])  # {"role","content","result","tool","out"}
    st.session_state.setdefault("n_calls", 0)

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.write(m["content"])
            else:
                st.write(m["result"].get("reply", ""))
                show_result(m["result"], m["tool"], m["out"])

    prompt = st.chat_input("예) 민트색 코바늘 버킷햇, 리본 달린 걸로")
    pending = st.session_state.pop("pending", None)  # 게이지 입력 버튼에서 온 요청
    text_in = prompt or pending
    if text_in:
        generate(text_in, tool, level, out)

    gauge_panel()


# =====================================================================
# 5. 뜨개샵 지도
# =====================================================================

KEYWORDS = ["털실", "뜨개질", "뜨개 공방", "니트 공방", "수예점"]
# 뜨개와 상관없는 곳(미용실, 도자기 공방 등)이 섞이지 않도록 좁게 유지
RELEVANT = ("털실", "뜨개", "뜨게", "니트", "수예", "knit", "yarn")
KEY = secret("KAKAO_REST_API_KEY")


@st.cache_data(ttl=3600, show_spinner=False)
def kakao_search(region, kw, key):
    out = []
    for page in (1, 2, 3):
        r = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": f"{region} {kw}", "page": page, "size": 15}, timeout=8)
        if r.status_code != 200:
            break
        j = r.json()
        out += j.get("documents", [])
        if j.get("meta", {}).get("is_end"):
            break
    return out


def page_map():
    header("뜨개샵 지도", "전국의 털실가게·뜨개 공방을 찾아보세요")
    left, right = st.columns([1, 3])
    with left:
        region = st.selectbox("지역", list(REGIONS))
        kws = st.multiselect("검색어", KEYWORDS, default=KEYWORDS[:3])
        show_comm = st.checkbox("친구들이 추천한 가게 보기", True)
        st.markdown("<span class='tag k'>빨강</span> 카카오맵 검색<br><span class='tag'>초록</span> 친구들 추천<br><span class='tag'>파랑</span> 내가 찍은 위치", unsafe_allow_html=True)
        if not KEY:
            st.info("카카오 API 키가 없어서 친구들이 추천한 가게만 보여요. (README 참고)")

    docs = {}
    if KEY:
        with st.spinner("뜨개샵을 찾는 중..."):
            for kw in kws:
                for d in kakao_search(region, kw, KEY):
                    name_cat = (d["place_name"] + " " + d.get("category_name", "")).lower()
                    if any(w in name_cat for w in RELEVANT):
                        docs[d["id"]] = d
    comm = q("SELECT * FROM shops WHERE region = :r ORDER BY id DESC", r=region) if show_comm else []

    lat, lon, zoom = REGIONS[region]
    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles="CartoDB positron")
    for d in docs.values():
        addr = d.get("road_address_name") or d.get("address_name", "")
        pop = (f"<b>{esc(d['place_name'])}</b><br>{esc(addr)}<br>{esc(d.get('phone', ''))}<br>"
               f"<a href='{esc(d.get('place_url', ''))}' target='_blank'>카카오맵에서 보기</a>")
        folium.Marker([float(d["y"]), float(d["x"])], popup=folium.Popup(pop, max_width=260),
                      tooltip=esc(d["place_name"]), icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    for s in comm:
        pop = f"<b>{esc(s['name'])}</b><br>{esc(s['address'])}<br>{esc(s['note'])}<br><i>추천: {esc(s['nick'])}</i>"
        folium.Marker([s["lat"], s["lon"]], popup=folium.Popup(pop, max_width=260),
                      tooltip=esc(s["name"]), icon=folium.Icon(color="green", icon="star")).add_to(m)
    pick = st.session_state.get("pick")
    if pick:
        folium.Marker([pick["lat"], pick["lng"]], tooltip="내가 찍은 위치",
                      icon=folium.Icon(color="blue", icon="map-marker")).add_to(m)

    with right:
        out = st_folium(m, height=520, use_container_width=True, key=f"map_{region}",
                        returned_objects=["last_clicked"])
        click = (out or {}).get("last_clicked")
        # 이미 등록에 쓴 클릭은 다시 핀으로 살아나지 않도록 무시
        if click and click != pick and click != st.session_state.get("used_click"):
            st.session_state.pick = click
            st.rerun()

    if docs:
        st.markdown(f"### {region} 검색 결과 {len(docs)}곳")
        st.dataframe(
            [{"이름": d["place_name"], "주소": d.get("road_address_name") or d.get("address_name", ""),
              "전화": d.get("phone", ""), "지도": d.get("place_url", "")} for d in docs.values()],
            hide_index=True, use_container_width=True,
            column_config={"지도": st.column_config.LinkColumn("카카오맵", display_text="열기")})
        st.caption("카카오맵 검색 결과라 뜨개와 상관없는 곳이 섞일 수 있어요. 방문 전 영업시간을 꼭 확인하세요!")

    st.markdown("### 아는 뜨개샵 추천하기")
    st.caption("위 지도에서 가게 위치를 클릭해 파란 핀을 찍은 뒤, 아래를 채워주세요." if not pick
               else f"선택한 위치: {pick['lat']:.5f}, {pick['lng']:.5f}  (다시 클릭하면 바뀌어요)")
    with st.form("shop_form", clear_on_submit=True):
        name = st.text_input("가게 이름", max_chars=40)
        addr = st.text_input("대략적인 주소 (동네까지)", max_chars=60)
        note = st.text_area("한줄 소개 (파는 실, 분위기 등)", max_chars=120)
        if st.form_submit_button("추천 등록"):
            nick = st.session_state.get("nickname", "")
            if not nick:
                st.warning("왼쪽 사이드바에서 닉네임을 먼저 정해주세요.")
            elif not (name.strip() and pick):
                st.warning("가게 이름을 쓰고, 지도에서 위치를 찍어주세요.")
            elif (msg := check_text(name, addr, note)):
                st.warning(msg)
            else:
                ex("INSERT INTO shops (name, region, address, lat, lon, note, nick, created) "
                   "VALUES (:n,:r,:a,:la,:lo,:no,:ni,:c)", n=name.strip(), r=region, a=addr.strip(),
                   la=pick["lat"], lo=pick["lng"], no=note.strip(), ni=nick, c=now())
                st.session_state.used_click = pick
                st.session_state.pick = None
                st.success("등록했어요. 고마워요!")
                st.rerun()


# =====================================================================
# 6. 뜨개모임 (커뮤니티)
# =====================================================================


def page_board():
    header("뜨개모임", "같이 뜰 친구를 찾고, 질문하고, 작품을 자랑해요")
    st.markdown("""<div class="safe-box"><b>안전 규칙</b><br>
    • 실명·학교·전화번호·SNS 아이디는 쓰지 않아요 (자동으로 막혀요). 소통은 댓글로!<br>
    • 오프라인 모임은 <b>카페·도서관·공방 같은 공공장소</b>에서, 낮 시간에, 보호자나 친구에게 알리고 가요.<br>
    • 불편한 글은 신고를 눌러주세요. 신고가 3번 쌓이면 자동으로 숨겨져요.</div>""", unsafe_allow_html=True)

    nick = st.session_state.get("nickname", "")
    if not nick:
        st.info("왼쪽 사이드바에서 닉네임을 정하면 글과 댓글을 쓸 수 있어요.")
    st.session_state.setdefault("reported", set())

    tab_board, tab_write = st.tabs(["게시판", "글쓰기"])

    with tab_board:
        f1, f2 = st.columns(2)
        kind_f = f1.selectbox("종류", ["전체"] + KINDS)
        region_f = f2.selectbox("지역", ["전체", "전국/온라인"] + list(REGIONS))
        posts = q("SELECT * FROM posts WHERE reports < 3 AND (:k = '전체' OR kind = :k) "
                  "AND (:r = '전체' OR region = :r) ORDER BY id DESC LIMIT 50", k=kind_f, r=region_f)
        comments = {}
        for c in reversed(q("SELECT * FROM comments ORDER BY id DESC LIMIT 1000")):
            comments.setdefault(c["post_id"], []).append(c)

        if not posts:
            st.write("아직 글이 없어요. 첫 글을 남겨보세요.")
        for p in posts:
            tags = f'<span class="tag k">{esc(p["kind"])}</span><span class="tag">{esc(p["region"])}</span>'
            if p["kind"] == KINDS[0]:
                tags += f'<span class="tag">{esc(p["place"])}</span><span class="tag">{esc(p["meet_date"])}</span>'
            st.markdown(
                f'<div class="knit-card">{tags}<h3>{esc(p["title"])}</h3><p>{esc(p["body"])}</p>'
                f'<span class="muted">{esc(p["nick"])} · {esc(p["created"])}</span></div>', unsafe_allow_html=True)
            cs = comments.get(p["id"], [])
            with st.expander(f"댓글 {len(cs)}개"):
                for c in cs:
                    st.markdown(f'<div class="cmt"><b>{esc(c["nick"])}</b> <span class="muted">{esc(c["created"])}</span>'
                                f'<br>{esc(c["body"])}</div>', unsafe_allow_html=True)
                with st.form(f"cf{p['id']}", clear_on_submit=True):
                    body = st.text_input("댓글", max_chars=200, label_visibility="collapsed",
                                         placeholder="참여할래요! / 응원해요 / 질문 답변...")
                    a, b = st.columns([3, 1])
                    send = a.form_submit_button("댓글 달기")
                    rep = b.form_submit_button("신고")
                if send:
                    if not nick:
                        st.warning("닉네임을 먼저 정해주세요.")
                    elif not body.strip():
                        st.warning("내용을 써주세요.")
                    elif (msg := check_text(body)):
                        st.warning(msg)
                    else:
                        ex("INSERT INTO comments (post_id, nick, body, created) VALUES (:p,:n,:b,:c)",
                           p=p["id"], n=nick, b=body.strip(), c=now())
                        st.rerun()
                if rep and p["id"] not in st.session_state.reported:
                    ex("UPDATE posts SET reports = reports + 1 WHERE id = :i", i=p["id"])
                    st.session_state.reported.add(p["id"])
                    st.toast("신고가 접수됐어요. 고마워요!")

    with tab_write:
        kind = st.selectbox("어떤 글인가요?", KINDS, key="w_kind")
        with st.form("post_form", clear_on_submit=True):
            title = st.text_input("제목", max_chars=40)
            body = st.text_area("내용", max_chars=500)
            region = st.selectbox("지역", ["전국/온라인"] + list(REGIONS))
            place, meet_date = "", ""
            if kind == KINDS[0]:
                place = st.text_input("모임 장소 (공공장소 이름만! 예: OO도서관, OO카페)", max_chars=40)
                meet_date = str(st.date_input("날짜"))
            ok = st.checkbox("안전 규칙을 읽었고, 개인정보는 쓰지 않았어요")
            if st.form_submit_button("올리기"):
                if not nick:
                    st.warning("닉네임을 먼저 정해주세요.")
                elif not (title.strip() and body.strip()):
                    st.warning("제목과 내용을 써주세요.")
                elif kind == KINDS[0] and not place.strip():
                    st.warning("모임 장소를 써주세요.")
                elif not ok:
                    st.warning("안전 규칙 확인에 체크해주세요.")
                elif time.time() - st.session_state.get("last_post", 0) < 20:
                    st.warning("너무 빨라요! 잠깐 쉬었다 올려주세요.")
                elif (msg := check_text(title, body, place)):
                    st.warning(msg)
                else:
                    ex("INSERT INTO posts (kind, title, body, nick, region, place, meet_date, created, reports) "
                       "VALUES (:k,:t,:b,:n,:r,:p,:d,:c,0)", k=kind, t=title.strip(), b=body.strip(), n=nick,
                       r=region, p=place.strip(), d=meet_date, c=now())
                    st.session_state.last_post = time.time()
                    st.success("올렸어요. 게시판 탭에서 확인해보세요.")


# =====================================================================
# 실행
# =====================================================================
setup()
{NAV[0]: page_home, NAV[1]: page_chat, NAV[2]: page_map, NAV[3]: page_board}[st.session_state.nav]()_state.nav]()
