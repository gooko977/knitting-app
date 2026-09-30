"""knit. - 홈 화면 (첫 화면)
실행: streamlit run main.py
"""
import streamlit as st

from common import setup

setup()  # 반드시 맨 처음

st.markdown("""
<div class="hero">
  <div class="wordmark xl">knit<span>.</span></div>
  <div class="tagline">말로 설명하면, 도안이 됩니다.</div>
  <p class="lede">만들고 싶은 뜨개를 설명하면 AI가 완성 이미지와 도안, 필요한 바늘 호수까지 정리해 드려요. 내 손 게이지를 넣으면 코수와 단수도 다시 계산해 줘요.</p>
  <span class="tag k">코바늘</span><span class="tag k">대바늘</span><span class="tag">호수 추천</span><span class="tag">케이블 길이</span><span class="tag">게이지 10×10cm</span>
</div>
<div class="stitch"></div>""", unsafe_allow_html=True)

CARDS = [
    ("01", "AI 도안", "아이디어를 말하면 완성 이미지와 단계별 도안을 만들어 줘요.", "pages/1_AI도안.py"),
    ("02", "뜨개모임", "함께 뜰 사람을 찾고, 질문하고, 작품을 나눠요.", "pages/2_뜨개모임.py"),
]
for col, (n, t, d, path) in zip(st.columns(2), CARDS):
    with col:
        st.markdown(f'<div class="knit-card"><div class="num">{n}</div><h3>{t}</h3><p>{d}</p></div>',
                    unsafe_allow_html=True)
        try:
            st.page_link(path, label=f"{t} 열기")
        except Exception:  # 파일 이름이 다르면 버튼 대신 안내
            st.caption("왼쪽 메뉴에서 열어 보세요.")
            """knit. - 뜨개모임 화면 (커뮤니티 게시판)"""
import time

import streamlit as st

from common import KINDS, REGIONS, check_text, esc, ex, header, now, q, setup

setup()  # 반드시 맨 처음

# =====================================================================
# 5. 뜨개모임 (커뮤니티)
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


page_board()
