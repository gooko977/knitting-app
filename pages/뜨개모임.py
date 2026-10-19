
import streamlit as st
from sqlalchemy import text

from common import (
    setup, header, esc, q, ex, now, engine,
    posts, comments, reports, KINDS, REGIONS,
    check_text, award_points
)

setup()
nick = st.session_state.nick
header("뜨개모임", "작품을 나누고, 질문하고, 함께 뜨개 이야기를 해 봐.")

st.info(
    "안전한 모임을 위해 게시글에 전화번호, 이메일, 외부 링크를 올리지 말아 줘. "
    "처음 만나는 사람과 만날 때는 보호자에게 알리고 공공장소를 이용해."
)

# -------------------------
# 게시글 작성
# -------------------------

with st.expander("＋ 새 게시글 작성", expanded=False):
    with st.form("new_post_form", clear_on_submit=True):
        kind = st.selectbox("게시글 종류", KINDS)
        region = st.selectbox("지역", REGIONS[1:])
        title = st.text_input("제목", max_chars=120)
        body = st.text_area("내용", max_chars=2000)

        submit_post = st.form_submit_button(
            "게시글 올리기",
            type="primary",
        )

    if submit_post:
        title_ok, clean_title = check_text(title, 120)
        body_ok, clean_body = check_text(body, 2000)

        if not title_ok:
            st.warning("제목을 1~120자로 입력해 줘.")
        elif not body_ok:
            st.warning(clean_body)
        else:
            try:
                with engine.begin() as conn:
                    result = conn.execute(
                        posts.insert().values(
                            nick=nick,
                            kind=kind,
                            region=region,
                            title=clean_title,
                            body=clean_body,
                            created_at=now(),
                            reports=0,
                        )
                    )
                    post_id = result.inserted_primary_key[0]

                awarded = award_points(
                    nick,
                    f"post:{post_id}",
                    5,
                    "커뮤니티 게시글 작성",
                )

                if awarded:
                    st.success("게시글을 올렸어! +5P")
                else:
                    st.success("게시글을 올렸어!")
                st.rerun()

            except Exception:
                st.error("게시글 저장에 실패했어. 잠시 후 다시 시도해 줘.")

st.divider()

# -------------------------
# 검색과 필터
# -------------------------

f1, f2, f3 = st.columns([1, 1, 1.4])

with f1:
    selected_kind = st.selectbox("종류", ["전체"] + KINDS)

with f2:
    selected_region = st.selectbox("지역", REGIONS)

with f3:
    keyword = st.text_input("검색", placeholder="제목이나 내용 검색")

conditions = ["COALESCE(reports, 0) < 3"]
params = {}

if selected_kind != "전체":
    conditions.append("kind = :kind")
    params["kind"] = selected_kind

if selected_region != "전체":
    conditions.append("region = :region")
    params["region"] = selected_region

if keyword.strip():
    # 검색어에 SQL 와일드카드가 포함되어도 쿼리 구조는 바뀌지 않음
    conditions.append("(title LIKE :keyword OR body LIKE :keyword)")
    params["keyword"] = "%" + keyword.strip() + "%"

where_sql = " AND ".join(conditions)

post_list = q(
    f"""
    SELECT id, nick, kind, region, title, body, created_at
    FROM posts
    WHERE {where_sql}
    ORDER BY id DESC
    LIMIT 100
    """,
    params,
)

st.subheader(f"게시글 {len(post_list)}개")

if not post_list:
    st.info("아직 게시글이 없어. 첫 게시글을 작성해 봐!")
else:
    for post in post_list:
        post_id = post["id"]

        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])

            with top_left:
                st.caption(
                    f"{post['kind']} · {post['region']} · "
                    f"{post['nick']} · {post['created_at']}"
                )
                st.markdown(f"### {esc(post['title'])}")
                st.write(post["body"])

            with top_right:
                if post["nick"] != nick:
                    if st.button(
                        "신고",
                        key=f"report_{post_id}",
                        help="부적절한 게시글을 신고해.",
                    ):
                        try:
                            with engine.begin() as conn:
                                conn.execute(
                                    reports.insert().values(
                                        post_id=post_id,
                                        reporter=nick,
                                        created_at=now(),
                                    )
                                )
                                conn.execute(
                                    posts.update()
                                    .where(posts.c.id == post_id)
                                    .values(
                                        reports=posts.c.reports + 1
                                    )
                                )
                            st.success("신고가 접수됐어.")
                            st.rerun()
                        except Exception:
                            st.info("이미 신고했거나 신고 처리에 실패했어.")

            comment_list = q(
                """
                SELECT id, nick, body, created_at
                FROM comments
                WHERE post_id = :post_id
                ORDER BY id ASC
                LIMIT 100
                """,
                {"post_id": post_id},
            )

            with st.expander(f"댓글 {len(comment_list)}개"):
                if comment_list:
                    for comment in comment_list:
                        st.markdown(
                            f"**{esc(comment['nick'])}** "
                            f"<span style='color:#7A736C;font-size:0.8rem'>"
                            f"{esc(comment['created_at'])}</span>",
                            unsafe_allow_html=True,
                        )
                        st.write(comment["body"])
                else:
                    st.caption("첫 댓글을 남겨 봐!")

                with st.form(
                    f"comment_form_{post_id}",
                    clear_on_submit=True,
                ):
                    comment_body = st.text_area(
                        "댓글 쓰기",
                        key=f"comment_body_{post_id}",
                        max_chars=500,
                        placeholder="서로 존중하는 댓글을 남겨 줘.",
                    )
                    submit_comment = st.form_submit_button("댓글 등록")

                if submit_comment:
                    valid, clean_comment = check_text(comment_body, 500)

                    if not valid:
                        st.warning(clean_comment)
                    else:
                        try:
                            with engine.begin() as conn:
                                result = conn.execute(
                                    comments.insert().values(
                                        post_id=post_id,
                                        nick=nick,
                                        body=clean_comment,
                                        created_at=now(),
                                    )
                                )
                                comment_id = result.inserted_primary_key[0]

                            awarded = award_points(
                                nick,
                                f"comment:{comment_id}",
                                2,
                                "커뮤니티 댓글 작성",
                            )

                            if awarded:
                                st.success("댓글을 등록했어! +2P")
                            else:
                                st.success("댓글을 등록했어!")
                            st.rerun()

                        except Exception:
                            st.error("댓글을 저장하지 못했어. 다시 시도해 줘.")

st.divider()
st.caption(
    "게시글은 최근 100개까지 표시돼. 신고가 3회 이상 접수된 글은 목록에서 숨겨져."
)
