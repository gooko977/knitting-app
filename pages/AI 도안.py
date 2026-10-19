
import streamlit as st
from google import genai

from common import setup, header, secret, esc

setup()
header("AI 도안", "원하는 작품을 설명하면 도안 초안을 만들어 줄게.")

st.markdown(
    """
    <div class="knit-card">
    <strong>사용 방법</strong><br>
    <span class="knit-muted">
    작품 종류와 크기, 원하는 실과 바늘을 입력해.
    게이지 정보가 있다면 함께 적어 주면 더 구체적인 초안을 만들 수 있어.
    </span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("pattern_form"):
    project_type = st.selectbox(
        "만들고 싶은 작품",
        ["가방", "인형", "목도리", "모자", "상의", "소품", "기타"],
    )
    skill = st.selectbox(
        "뜨개 경험",
        ["초보자", "기초를 알고 있음", "중급", "숙련자"],
    )
    method = st.radio(
        "뜨개 방식",
        ["코바늘", "대바늘", "둘 다 가능"],
        horizontal=True,
    )

    size = st.text_input(
        "완성 크기",
        placeholder="예: 가로 20cm, 세로 16cm",
    )
    yarn = st.text_input(
        "사용할 실",
        placeholder="예: 면사, 권장 바늘 3mm",
    )
    needle = st.text_input(
        "바늘 크기",
        placeholder="예: 코바늘 3호",
    )
    gauge = st.text_input(
        "게이지 (선택)",
        placeholder="예: 10cm에 22코, 26단",
    )
    request = st.text_area(
        "추가 요청",
        placeholder="예: 단순한 모양, 초보자도 따라 할 수 있게 설명해 줘.",
        max_chars=1500,
    )

    submitted = st.form_submit_button("도안 만들기", type="primary")

if submitted:
    api_key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")

    if not api_key:
        st.error(
            "API 키가 설정되지 않았어. "
            "Streamlit 비밀 정보에 GEMINI_API_KEY를 등록해 줘."
        )
    else:
        prompt = f"""
너는 뜨개 도안을 설명하는 친절한 보조 디자이너야.
한국어로, 실제로 따라 하기 쉬운 초안을 작성해.

[작품 정보]
종류: {project_type}
경험 수준: {skill}
방식: {method}
완성 크기: {size or '미정'}
실: {yarn or '미정'}
바늘: {needle or '미정'}
게이지: {gauge or '미입력'}
추가 요청: {request or '특별한 요청 없음'}

다음 순서로 작성해.
1. 도안 제목과 완성 모습
2. 준비물
3. 시작하기 전 확인할 사항
4. 단계별 작업 순서
5. 코 수와 단 수가 달라질 때의 조정 방법
6. 마무리 방법
7. 주의할 점

중요:
- 게이지가 없으면 정확한 코 수를 확정값처럼 말하지 말고 시험편을 권장해.
- 실의 굵기나 개인의 손땀에 따라 결과가 달라질 수 있음을 알려 줘.
- 불확실한 수치는 추정치라고 표시해.
- 초보자가 선택되면 뜨개 용어를 짧게 설명해.
- 기존 출판 도안의 문장을 그대로 재현하지 말고 새롭게 설명해.
"""

        with st.spinner("도안을 만드는 중이야..."):
            try:
                client = genai.Client(api_key=api_key)
                model_name = secret("GEMINI_MODEL", "gemini-2.5-flash")

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                answer = getattr(response, "text", None)

                if answer:
                    st.session_state["latest_pattern"] = answer
                    st.session_state["latest_pattern_title"] = project_type
                else:
                    st.error("응답이 비어 있어. 조건을 바꿔 다시 시도해 줘.")

            except Exception as error:
                st.error(
                    "AI 요청에 실패했어. API 키, 모델 이름, "
                    "인터넷 연결과 사용량 한도를 확인해 줘."
                )
                st.caption(f"오류 유형: {type(error).__name__}")

if st.session_state.get("latest_pattern"):
    st.divider()
    st.subheader(
        f"생성된 도안 · {st.session_state.get('latest_pattern_title', '')}"
    )
    st.markdown(st.session_state["latest_pattern"])

    st.download_button(
        "도안 텍스트 저장하기",
        data=st.session_state["latest_pattern"],
        file_name="knit_pattern.txt",
        mime="text/plain",
    )

    st.divider()
    st.subheader("도안 수정하기")

    with st.form("pattern_revision_form"):
        revision = st.text_area(
            "어떤 부분을 바꾸고 싶어?",
            placeholder="예: 손잡이를 더 짧게 하고 초보자용으로 설명해 줘.",
        )
        revise = st.form_submit_button("도안 수정 요청")

    if revise:
        api_key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")

        if not api_key:
            st.error("API 키가 없어.")
        elif not revision.strip():
            st.warning("수정할 내용을 입력해 줘.")
        else:
            with st.spinner("도안을 수정하고 있어..."):
                try:
                    client = genai.Client(api_key=api_key)
                    model_name = secret("GEMINI_MODEL", "gemini-2.5-flash")

                    response = client.models.generate_content(
                        model=model_name,
                        contents=(
                            "아래 뜨개 도안을 요청에 맞게 수정해 줘. "
                            "한국어로 단계별 설명을 유지해.\n\n"
                            "기존 도안:\n"
                            + st.session_state["latest_pattern"]
                            + "\n\n수정 요청:\n"
                            + revision
                        ),
                    )

                    if getattr(response, "text", None):
                        st.session_state["latest_pattern"] = response.text
                        st.rerun()
                    else:
                        st.error("수정 결과가 비어 있어.")

                except Exception as error:
                    st.error("수정 요청에 실패했어.")
                    st.caption(f"오류 유형: {type(error).__name__}")

st.caption(
    "AI가 만든 도안은 초안이야. 실제 작업 전에 게이지와 코 수를 확인해 줘."
)
