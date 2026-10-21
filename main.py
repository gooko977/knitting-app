import streamlit as st
import streamlit.components.v1 as components

from common import setup, get_user_stats, q

setup()
nick = st.session_state.nick


def make_cat(points):
    points = max(0, points)
    growth = min(points / 1500, 1)
    length = int(25 + 65 * growth)
    bottom = 170 + length

    if points >= 1500:
        accessory = """
        <path d="M150 82 L150 52 L170 66 L190 40
                 L210 66 L230 52 L230 82 Z"
              fill="#E9B949"/>
        <g fill="#E9B949">
          <circle cx="115" cy="92" r="4"/>
          <circle cx="275" cy="105" r="4"/>
          <circle cx="250" cy="50" r="4"/>
        </g>
        """
        needle = "#D8A72E"
    elif points >= 700:
        accessory = """
        <path d="M145 83 Q145 40 190 40 Q235 40 235 83 Z"
              fill="#B9B7C3"/>
        <path d="M145 76 Q190 90 235 76 L235 91
                 Q190 102 145 91 Z" fill="#D4D1DC"/>
        """
        needle = "#B9B7C3"
    elif points >= 300:
        accessory = """
        <g fill="none" stroke="#5B514B" stroke-width="4">
          <circle cx="170" cy="118" r="17"/>
          <circle cx="210" cy="118" r="17"/>
          <path d="M187 118 L193 118"/>
        </g>
        """
        needle = "#A7A9AC"
    elif points >= 100:
        accessory = """
        <path d="M166 78 Q145 51 137 72 Q145 91 166 85 Z"
              fill="#B5502E"/>
        <path d="M166 78 Q187 51 195 72 Q187 91 166 85 Z"
              fill="#D77A58"/>
        """
        needle = "#9A6948"
    else:
        accessory = ""
        needle = "#C7A477"

    rows = "".join(
        f'<path d="M176 {y} Q190 {y-4} 204 {y}" '
        'stroke="#F2B59A" stroke-width="2" fill="none"/>'
        for y in range(180, bottom, 9)
    )

    return f"""
    <div class="stage">
      <svg viewBox="0 0 380 310" role="img"
           aria-label="성장하는 뜨개 고양이">
        <ellipse cx="190" cy="282" rx="92" ry="12"
                 fill="#D9CEC2" opacity=".6"/>

        <path class="tail"
              d="M245 220 Q294 225 283 184 Q278 164 261 174"
              fill="none" stroke="#F3E9DD"
              stroke-width="21" stroke-linecap="round"/>

        <ellipse cx="190" cy="218" rx="72" ry="66"
                 fill="#FFFDF9" stroke="#E7DDD2" stroke-width="2"/>

        <path d="M137 100 L142 54 Q145 43 157 55 L179 84 Z"
              fill="#FFFDF9" stroke="#E7DDD2" stroke-width="3"/>
        <path d="M146 78 L150 60 L165 82 Z" fill="#E8A6A0"/>

        <path d="M201 84 L224 55 Q236 43 238 55 L243 100 Z"
              fill="#FFFDF9" stroke="#E7DDD2" stroke-width="3"/>
        <path d="M215 82 L232 60 L233 78 Z" fill="#E8A6A0"/>

        <circle cx="190" cy="116" r="61"
                fill="#FFFDF9" stroke="#E7DDD2" stroke-width="3"/>

        <g class="eyes" fill="#302923">
          <ellipse cx="170" cy="115" rx="4.5" ry="6.5"/>
          <ellipse cx="210" cy="115" rx="4.5" ry="6.5"/>
        </g>

        <ellipse cx="155" cy="132" rx="10" ry="5"
                 fill="#EBAAA0" opacity=".7"/>
        <ellipse cx="225" cy="132" rx="10" ry="5"
                 fill="#EBAAA0" opacity=".7"/>
        <path d="M185 126 Q190 133 195 126
                 Q193 137 190 137 Q187 137 185 126"
              fill="#D78A82"/>
        <path d="M190 137 Q182 145 178 138
                 M190 137 Q198 145 202 138"
              fill="none" stroke="#6A5149" stroke-width="2.5"
              stroke-linecap="round"/>

        {accessory}

        <path d="M151 155 Q190 170 229 155 L225 174
                 Q190 189 155 174 Z" fill="#B5502E"/>

        <path d="M172 166 L172 {bottom}
                 Q190 {bottom+7} 208 {bottom} L208 166 Z"
              fill="#C76645" stroke="#A7472B" stroke-width="2"/>
        {rows}

        <g class="needles" stroke="{needle}" stroke-width="4"
           stroke-linecap="round">
          <path d="M135 190 L218 151"/>
          <path d="M160 151 L235 190"/>
        </g>

        <ellipse cx="158" cy="269" rx="27" ry="12" fill="#FFFDF9"/>
        <ellipse cx="222" cy="269" rx="27" ry="12" fill="#FFFDF9"/>
      </svg>
    </div>

    <style>
      .stage {{
        background:#F3EFE9;
        border-radius:22px;
        display:flex;
        justify-content:center;
        overflow:hidden;
      }}
      .stage svg {{width:100%;max-width:380px;height:auto}}
      .tail {{
        transform-origin:260px 190px;
        animation:wag 2.2s ease-in-out infinite;
      }}
      .eyes {{transform-origin:center;animation:blink 4s infinite}}
      .needles {{
        transform-origin:190px 170px;
        animation:knit 1.3s ease-in-out infinite alternate;
      }}
      @keyframes wag {{
        0%,100% {{transform:rotate(-5deg)}}
        50% {{transform:rotate(9deg)}}
      }}
      @keyframes blink {{
        0%,44%,48%,100% {{transform:scaleY(1)}}
        46% {{transform:scaleY(.08)}}
      }}
      @keyframes knit {{
        from {{transform:rotate(-3deg)}}
        to {{transform:rotate(3deg)}}
      }}
      @media(prefers-reduced-motion:reduce) {{
        .tail,.eyes,.needles {{animation:none}}
      }}
    </style>
    """


st.title("knit.")
st.caption("말로 설명하면, 도안이 됩니다.")
st.divider()

stats = get_user_stats(nick)
points = stats["points"]

left, right = st.columns([1.05, 1], gap="large")

with left:
    st.subheader("나의 뜨개 친구")
    components.html(make_cat(points), height=320, scrolling=False)

with right:
    st.subheader("나의 성장 기록")
    st.caption(f"{nick}의 뜨개 여정")
    st.metric("모은 포인트", f"{points:,}P")
    st.markdown(f"**현재 레벨 · {stats['level']}**")
    st.write(f"레벨 아이템: {stats['item']}")

    if stats["next_level"]:
        st.progress(stats["progress"])
        st.caption(
            f"다음 레벨까지 {stats['remaining']:,}P 남았어!"
        )
    else:
        st.progress(1.0)
        st.success("최고 레벨에 도달했어!")

st.divider()
st.subheader("knit. 둘러보기")
st.caption("뜨개 생활에 필요한 기능을 이용해 봐.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### 📝 뜨개 기록장")
    st.write("작품의 실, 바늘, 게이지와 작업 과정을 기록해.")
    if st.button("기록장 열기", use_container_width=True):
        st.switch_page("pages/뜨개 기록장.py")

with col2:
    st.markdown("### ✨ AI 도안")
    st.write("원하는 작품을 설명하고 도안 초안을 만들어 봐.")
    if st.button("AI 도안 열기", use_container_width=True):
        st.switch_page("pages/AI 도안.py")

st.markdown("### 🧶 뜨개모임")
st.write("작품을 공유하고 다른 뜨개러들과 이야기를 나눠 봐.")
if st.button("뜨개모임 열기", use_container_width=True):
    st.switch_page("pages/뜨개모임.py")

st.caption("포인트는 기록장·AI 도안·뜨개모임 활동을 통해 모을 수 있어.")
