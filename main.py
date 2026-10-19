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
    ("01", "AI 도안", "아이디어를 말하면 완성 이미지와 단계별 도안을 만들어 줘요.", "pages/AI 도안.py"),
    ("02", "뜨개모임", "함께 뜰 사람을 찾고, 질문하고, 작품을 나눠요.", "pages/뜨개모임.py"),
]
for col, (n, t, d, path) in zip(st.columns(2), CARDS):
    with col:
        st.markdown(f'<div class="knit-card"><div class="num">{n}</div><h3>{t}</h3><p>{d}</p></div>',
                    unsafe_allow_html=True)
        try:
            st.page_link(path, label=f"{t} 열기")
        except Exception:  # 파일 이름이 다르면 버튼 대신 안내
            st.caption("왼쪽 메뉴에서 열어 보세요.")
<div class="stitch"></div>""", unsafe_allow_html=True)

# 뜨개 고양이 캐릭터 (별도 이미지 파일 불필요)
st.markdown("""
<div style="text-align:center; padding:20px 0 30px;">
<svg viewBox="0 0 320 300" width="260"
     style="max-width:100%; height:auto;"
     xmlns="http://www.w3.org/2000/svg">

  <!-- 그림자 -->
  <ellipse cx="160" cy="265" rx="85" ry="12"
           fill="#E8DFD5"/>

  <!-- 귀 -->
  <path d="M88 100 L83 35 Q82 25 94 34 L132 72 Z"
        fill="#F5E9D9" stroke="#D8C8B7" stroke-width="2"/>
  <path d="M94 67 L92 46 L112 72 Z" fill="#DDA6A0"/>

  <path d="M188 72 L226 34 Q238 25 237 39 L232 103 Z"
        fill="#F5E9D9" stroke="#D8C8B7" stroke-width="2"/>
  <path d="M207 70 L229 46 L226 78 Z" fill="#DDA6A0"/>

  <!-- 몸통 -->
  <ellipse cx="160" cy="205" rx="76" ry="63"
           fill="#F7EFE4" stroke="#D8C8B7" stroke-width="2"/>

  <!-- 얼굴 -->
  <circle cx="160" cy="116" r="69"
          fill="#FFF8EE" stroke="#D8C8B7" stroke-width="2"/>

  <!-- 눈 -->
  <ellipse cx="137" cy="116" rx="5" ry="7" fill="#352A26"/>
  <ellipse cx="183" cy="116" rx="5" ry="7" fill="#352A26"/>

  <!-- 볼 -->
  <ellipse cx="120" cy="132" rx="12" ry="6" fill="#E9B5AD" opacity=".8"/>
  <ellipse cx="200" cy="132" rx="12" ry="6" fill="#E9B5AD" opacity=".8"/>

  <!-- 코와 입 -->
  <path d="M154 128 Q160 122 166 128 Q160 137 154 128"
        fill="#B86F70"/>
  <path d="M160 135 Q153 144 148 138 M160 135 Q167 144 172 138"
        fill="none" stroke="#665047" stroke-width="2"
        stroke-linecap="round"/>

  <!-- 목도리 -->
  <path d="M104 164 Q160 184 216 164 L209 185
           Q160 204 111 185 Z"
        fill="#B5502E"/>
  <path d="M174 184 L197 188 L188 228 L165 223 Z"
        fill="#B5502E"/>
  <path d="M174 194 L191 197 M171 204 L189 207
           M169 214 L187 217"
        stroke="#D98A68" stroke-width="2"/>

  <!-- 뜨개 바늘 -->
  <path d="M83 211 L147 174"
        stroke="#B98A57" stroke-width="5"
        stroke-linecap="round"/>
  <path d="M80 209 L76 205"
        stroke="#B98A57" stroke-width="3"
        stroke-linecap="round"/>

  <path d="M226 211 L172 174"
        stroke="#B98A57" stroke-width="5"
        stroke-linecap="round"/>
  <path d="M229 209 L233 205"
        stroke="#B98A57" stroke-width="3"
        stroke-linecap="round"/>

  <!-- 작은 편물 -->
  <path d="M126 207 L153 198 L166 221
           L158 243 L130 240 L119 220 Z"
        fill="#D9A17C" stroke="#B9815E" stroke-width="2"/>
  <path d="M129 214 L155 210 M126 222 L161 219
           M130 231 L158 229 M137 205 L140 239
           M148 202 L150 240"
        stroke="#F1D0B3" stroke-width="2"
        stroke-linecap="round"/>

  <!-- 발 -->
  <ellipse cx="126" cy="251" rx="26" ry="14" fill="#FFF8EE"/>
  <ellipse cx="194" cy="251" rx="26" ry="14" fill="#FFF8EE"/>

</svg>
<div style="font-size:14px; color:#8B776A;
            letter-spacing:2px; margin-top:5px;">
  little knitting buddy
</div>
</div>
""", unsafe_allow_html=True)
