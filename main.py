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
