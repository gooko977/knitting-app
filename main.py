
# -------------------------
# 메인 페이지 메뉴
# -------------------------

st.divider()
st.subheader("knit. 둘러보기")
st.caption("뜨개 생활에 필요한 기능을 이용해 봐.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        """
        <div class="knit-card">
            <h3>✨ AI 도안</h3>
            <p>원하는 작품을 설명하고 나만의 뜨개 도안을 만들어 봐.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("AI 도안 열기", use_container_width=True):
        st.switch_page("pages/AI 도안.py")

with col2:
    st.markdown(
        """
        <div class="knit-card">
            <h3>🧶 뜨개모임</h3>
            <p>작품을 공유하고 다른 뜨개러들과 이야기를 나눠 봐.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("뜨개모임 열기", use_container_width=True):
        st.switch_page("pages/뜨개모임.py")
