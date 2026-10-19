
import streamlit as st
from datetime import date

from common import (
    setup, header, esc, q, ex, now,
    check_text, get_user_stats, award_points
)

setup()
nick = st.session_state.nick

def cat_svg(level_index):
    """레벨별 장식이 바뀌는 간단한 SVG 고양이."""
    accessories = [
        '<path d="M108 84 L120 63 L132 84 Z" fill="#C89B65"/>',
        '<path d="M106 76 Q120 61 134 76" fill="none" stroke="#8B5E3C" stroke-width="7" stroke-linecap="round"/>',
        '<circle cx="105" cy="105" r="10" fill="none" stroke="#6B5144" stroke-width="4"/><circle cx="135" cy="105" r="10" fill="none" stroke="#6B5144" stroke-width="4"/><path d="M115 105 H125" stroke="#6B5144" stroke-width="3"/>',
        '<path d="M103 75 Q120 49 137 75 Z" fill="#B5502E"/><circle cx="120" cy="61" r="5" fill="#F5D7A2"/>',
        '<path d="M102 74 L110 51 L120 63 L130 51 L138 74 Z" fill="#D5A84C"/><circle cx="120" cy="59" r="4" fill="#FFF1B8"/>',
    ]
    accessory = accessories[max(0, min(level_index, 4))]
    return f"""
    <svg viewBox="0 0 240 245" width="100%" role="img"
         aria-label="뜨개 고양이 캐릭터">
      <ellipse cx="120" cy="220" rx="64" ry="10" fill="#E5DCD2"/>
      <path d="M77 99 L73 43 Q73 34 83 41 L111 65
               Q120 61 129 65 L157 41 Q167 34 167 43 L163 99"
            fill="#F7F0E7" stroke="#D8CFC4" stroke-width="3"
            stroke-linejoin="round"/>
      <path d="M83 54 L101 70 L86 82 Z" fill="#DDA7A0"/>
      <path d="M157 54 L139 70 L154 82 Z" fill="#DDA7A0"/>
      <ellipse cx="120" cy="133" rx="57" ry="63"
               fill="#FFFDF9" stroke="#D8CFC4" stroke-width="3"/>
      <ellipse cx="101" cy="127" rx="5" ry="7" fill="#292522"/>
      <ellipse cx="139" cy="127" rx="5" ry="7" fill="#292522"/>
      <path d="M116 139 Q120 144 124 139"
            fill="none" stroke="#B87E73" stroke-width="3"
            stroke-linecap="round"/>
      <ellipse cx="91" cy="143" rx="9" ry="5" fill="#E9B8AC" opacity=".7"/>
      <ellipse cx="149" cy="143" rx="9" ry="5" fill="#E9B8AC" opacity=".7"/>
      <path d="M70 160 Q120 180 170 160 L166 183
               Q120 203 74 183 Z" fill="#B5502E"/>
      <path d="M99 171 L104 196 L117 192 L112 172 Z" fill="#C66B48"/>
      <path d="M158 191 L173 180" stroke="#A17A50"
            stroke-width="5" stroke-linecap="round"/>
      <path d="M169 179 L182 166" stroke="#A17A50"
            stroke-width="3" stroke-linecap="round"/>
      <path d="M181 165 L190 155" stroke="#A17A50"
            stroke-width="3" stroke-linecap="round"/>
      <path d="M184 161 L193 170" stroke="#A17A50"
            stroke-width="3" stroke-linecap="round"/>
      {accessory}
    </svg>
    """

header("나만의 뜨개 공간", "한 코씩 쌓아 가는 나의 작은 기록.")

stats = get_user_stats(nick)

left, right = st.columns([1, 1.25], gap="large")

with left:
    st.markdown('<div class="knit-card">', unsafe_allow_html=True)
    st.markdown(
        cat_svg(
            [0, 100, 300, 700, 1500].index(
                max(v for v in [0, 100, 300, 700, 1500] if stats["points"] >= v)
            )
        ),
        unsafe_allow_html=True,
    )
    st.markdown(f"### {esc(nick)}")
    st.markdown(f"**{esc(stats['level'])}**")
    st.caption(f"현재 장비 · {stats['item']}")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("### 나의 성장")
    a, b = st.columns(2)
    a.metric("모은 포인트", f"{stats['points']} P")
    b.metric("다음 레벨까지", f"{stats['remaining']} P")

    if stats["next_level"]:
        st.progress(stats["progress"])
        st.caption(
            f"다음 목표: {stats['next_level'][1]} "
            f"({stats['next_level'][0]} P)"
        )
    else:
        st.success("최고 레벨에 도달했어!")

    st.markdown(
        """
        <div class="knit-card">
        <strong>포인트를 모으는 방법</strong><br>
        <span class="knit-muted">
        매일 뜨개 기록 작성 +5P · 게시글 작성 +5P · 댓글 작성 +2P
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.subheader("오늘의 뜨개 기록")
st.caption("단수 자체가 아니라, 오늘의 작업을 기록한 것에 포인트를 지급해.")

with st.form("daily_record_form", clear_on_submit=True):
    project = st.text_input(
        "작품 이름",
        placeholder="예: 크림색 미니 가방",
        max_chars=80,
    )
    content = st.text_area(
        "오늘 무엇을 했나요?",
        placeholder="예: 손잡이 부분을 만들고 실 색을 정리했다.",
        max_chars=1000,
    )
    submitted = st.form_submit_button("기록 저장하기", type="primary")

if submitted:
    ok_project, project_value = check_text(project, 80)
    ok_content, content_value = check_text(content, 1000)

    if not ok_project:
        st.warning("작품 이름을 입력해 줘.")
    elif not ok_content:
        st.warning(content_value)
    else:
        today = date.today().isoformat()
        already = q(
            """
            SELECT id FROM records
            WHERE nick = :nick AND record_date = :day
            LIMIT 1
            """,
            {"nick": nick, "day": today},
        )

        if already:
            st.info("오늘의 기록은 이미 저장했어. 내일 다시 기록해 줘!")
        else:
            with __import__("common").engine.begin() as conn:
                conn.execute(
                    __import__("common").records.insert().values(
                        nick=nick,
                        record_date=today,
                        project=project_value,
                        content=content_value,
                        created_at=now(),
                    )
                )

            award_points(
                nick,
                f"daily-record:{today}",
                5,
                "오늘의 뜨개 기록",
            )
            st.success("기록을 저장했어! +5P")
            st.rerun()

st.subheader("최근 기록")

recent = q(
    """
    SELECT record_date, project, content
    FROM records
    WHERE nick = :nick
    ORDER BY id DESC
    LIMIT 5
    """,
    {"nick": nick},
)

if not recent:
    st.info("아직 기록이 없어. 첫 번째 뜨개 기록을 남겨 봐!")
else:
    for record in recent:
        with st.container(border=True):
            st.caption(record["record_date"])
            st.markdown(f"**{esc(record['project'])}**")
            st.write(record["content"])

st.divider()
st.subheader("바로 가기")

c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🧶 AI 도안")
    st.write("원하는 작품을 말로 설명하고 도안을 만들어 봐.")
    if st.button("AI 도안 열기", use_container_width=True):
        st.switch_page("pages/AI 도안.py")

with c2:
    st.markdown("### 🪡 뜨개모임")
    st.write("작품을 공유하고 다른 뜨개러들과 이야기해 봐.")
    if st.button("뜨개모임 열기", use_container_width=True):
        st.switch_page("pages/뜨개모임.py")

st.caption("knit. · 나만의 속도로, 한 코씩.")
