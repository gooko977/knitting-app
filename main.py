
import streamlit as st
from common import setup

setup()

st.title("knit.")
st.caption("말로 설명하면, 도안이 됩니다.")

st.divider()
st.subheader("knit. 둘러보기")
st.caption("뜨개 생활에 필요한 기능을 이용해 봐.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### ✨ AI 도안")
    st.write("원하는 작품의 뜨개 도안을 만들어 봐.")

    if st.button("AI 도안 열기", use_container_width=True):
        st.switch_page("pages/AI 도안.py")

with col2:
    st.markdown("### 🧶 뜨개모임")
    st.write("작품을 공유하고 다른 뜨개러들과 이야기를 나눠 봐.")

    if st.button("뜨개모임 열기", use_container_width=True):
        st.switch_page("pages/뜨개모임.py")
