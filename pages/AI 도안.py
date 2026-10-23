
import streamlit as st
from google import genai

from common import setup, header, secret, esc


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
setup()
header("AI 도안", "원하는 작품을 설명하면 도안 초안을 만들어 줄게.")


# --------------------------------------------------
# Gemini 공통 설정 및 요청 함수
# --------------------------------------------------
def get_gemini_client():
    """Secrets 또는 환경 변수에서 API 설정을 읽는다."""
    api_key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")

    if not api_key:
        st.error(
            "API 키가 설정되지 않았어. "
            "GEMINI_API_KEY 또는 GOOGLE_API_KEY를 등록해 줘."
        )
        return None, None

    # 기본 모델을 gemini-3.8-flash로 변경
    model_name = secret("GEMINI_MODEL", "gemini-3.8-flash")

    if not model_name or not str(model_name).strip():
        st.error("GEMINI_MODEL 설정이 비어 있어.")
        return None, None

    try:
        client = genai.Client(api_key=api_key)
        return client, str(model_name).strip()

    except Exception as error:
        show_api_error(error, "AI 클라이언트 초기화")
        return None, None


def show_api_error(error, action="AI 요청"):
    """API 오류 유형과 상세 내용을 표시한다."""
    st.error(f"{action}에 실패했어.")
    st.caption(f"오류 유형: {type(error).__name__}")

    error_code = getattr(error, "code", None)
    error_message = getattr(error, "message", None)
    error_status = getattr(error, "status", None)

    if error_code is not None:
        st.caption(f"오류 코드: {error_code}")

    if error_status:
        st.caption(f"오류 상태: {error_status}")

    if error_message:
        st.error(f"상세 내용: {error_message}")
    else:
        detail = str(error).strip()

        if detail:
            st.error(f"상세 내용: {detail}")
        else:
            st.info("상세 오류 메시지를 확인할 수 없어.")


def generate_text(prompt, action="AI 요청"):
    """Gemini에 요청하고 생성된 텍스트를 반환한다."""
    client, model_name = get_gemini_client()

    if client is None:
        return None

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        answer = getattr(response, "text", None)

        if answer and answer.strip():
            return answer.strip()

        st.warning(
            "AI 응답이 비어 있어. "
            "요청 내용을 조금 바꿔서 다시 시도해 줘."
        )
        return None

    except Exception as error:
        show_api_error(error, action)
        return None


# --------------------------------------------------
# 사용 방법
# --------------------------------------------------
st.markdown(
    """
    <div class="knit-card">
        <strong>사용 방법</strong><br>
        <span class="knit-muted">
            작품 종류와 크기, 원하는 실과 바늘을 입력해.
            게이지 정보가 있다면 함께 적어 주면 더 구체적인
            초안을 만들 수 있어.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 도안 생성 입력 폼
# --------------------------------------------------
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

    submitted = st.form_submit_button(
        "도안 만들기",
        type="primary",
    )


# --------------------------------------------------
# 도안 생성 처리
# --------------------------------------------------
if submitted:
    prompt = f"""
너는 뜨개 도안을 설명하는 친절한 보조 디자이너야.
한국어로, 실제로 따라 하기 쉬운 새로운 도안 초안을 작성해.

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

작성 규칙:
- 게이지가 없으면 정확한 코 수를 확정값처럼 말하지 말고 시험편을 권장해.
- 실의 굵기와 개인의 손땀에 따라 결과가 달라질 수 있음을 알려 줘.
- 불확실한 수치는 추정치라고 표시해.
- 초보자가 선택되면 뜨개 용어를 짧게 설명해.
- 코바늘과 대바늘의 작업 방법을 혼동하지 마.
- 작품의 형태와 크기에 맞는 작업 순서를 제시해.
- 기존 출판 도안의 문장을 그대로 재현하지 말고 새롭게 설명해.
- 실제 작업 전에 확인해야 하는 부분도 안내해.
"""

    with st.spinner("도안을 만드는 중이야..."):
        answer = generate_text(prompt, "도안 생성")

        if answer:
            st.session_state["latest_pattern"] = answer
            st.session_state["latest_pattern_title"] = project_type


# --------------------------------------------------
# 생성된 도안 표시
# --------------------------------------------------
latest_pattern = st.session_state.get("latest_pattern")

if latest_pattern:
    st.divider()

    st.subheader(
        f"생성된 도안 · "
        f"{st.session_state.get('latest_pattern_title', '')}"
    )

    st.markdown(latest_pattern)

    st.download_button(
        "도안 텍스트 저장하기",
        data=latest_pattern,
        file_name="knit_pattern.txt",
        mime="text/plain",
        key="download_pattern",
    )

    st.divider()
    st.subheader("도안 수정하기")

    # ----------------------------------------------
    # 도안 수정 입력 폼
    # ----------------------------------------------
    with st.form("pattern_revision_form"):
        revision = st.text_area(
            "어떤 부분을 바꾸고 싶어?",
            placeholder="예: 손잡이를 더 짧게 하고 초보자용으로 설명해 줘.",
            key="pattern_revision_input",
        )

        revise = st.form_submit_button("도안 수정 요청")

    # ----------------------------------------------
    # 도안 수정 처리
    # ----------------------------------------------
    if revise:
        if not revision.strip():
            st.warning("수정할 내용을 입력해 줘.")

        else:
            revision_prompt = f"""
너는 뜨개 도안을 수정하는 친절한 보조 디자이너야.
아래 도안을 사용자의 요청에 맞게 수정해 줘.
한국어로 단계별 설명을 유지하고, 수정된 전체 도안을 작성해.

[기존 도안]
{latest_pattern}

[수정 요청]
{revision}

작성 규칙:
- 수정 요청을 반영한 전체 도안을 보여 줘.
- 수정과 관계없는 기존 도안의 중요한 정보는 유지해.
- 코 수나 단 수를 정확히 확정하기 어려우면 그 점을 밝혀 줘.
- 실과 바늘, 게이지에 따른 차이를 고려해.
- 기존 출판 도안의 문장을 그대로 재현하지 말고 새롭게 설명해.
"""

            with st.spinner("도안을 수정하고 있어..."):
                revised_answer = generate_text(
                    revision_prompt,
                    "도안 수정",
                )

                if revised_answer:
                    st.session_state["latest_pattern"] = revised_answer
                    st.rerun()


# --------------------------------------------------
# 안내
# --------------------------------------------------
st.caption(
    "AI가 만든 도안은 초안이야. "
    "실제 작업 전에 게이지와 코 수를 확인해 줘."
)
