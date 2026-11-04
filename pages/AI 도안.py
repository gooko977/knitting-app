@@ -1,4 +1,6 @@

import os
import time
import streamlit as st
from google import genai

@@ -11,91 +13,175 @@
setup()
header("AI 도안", "원하는 작품을 설명하면 도안 초안을 만들어 줄게.")

# 기존 도안 저장 공간 초기화
if "latest_pattern" not in st.session_state:
    st.session_state["latest_pattern"] = None

# --------------------------------------------------
# Gemini 공통 설정 및 요청 함수
# --------------------------------------------------

# 사용할 Gemini 모델
GEMINI_MODEL = "gemini-3.8-flash"
if "latest_pattern_title" not in st.session_state:
    st.session_state["latest_pattern_title"] = ""


# --------------------------------------------------
# Gemini API 설정
# --------------------------------------------------
def get_gemini_client():
    """Secrets 또는 환경 변수에서 API 설정을 읽는다."""
    """Gemini API 클라이언트를 생성한다."""

    api_key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")
    api_key = (
        secret("GEMINI_API_KEY")
        or secret("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    model_name = (
        secret("GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL")
        or "gemini-3.8-flash"
    )

    if not api_key:
        st.error(
            "API 키가 설정되지 않았어. "
            "GEMINI_API_KEY 또는 GOOGLE_API_KEY를 등록해 줘."
            "Gemini API 키를 찾을 수 없어. "
            "Streamlit Secrets 설정을 확인해 줘."
        )
        return None, None

    try:
        client = genai.Client(api_key=api_key)
        return client, GEMINI_MODEL
        return client, model_name

    except Exception as error:
        show_api_error(error, "AI 클라이언트 초기화")
        st.error("Gemini API 클라이언트를 생성하지 못했어.")
        st.caption(f"상세 내용: {error}")
        return None, None


# --------------------------------------------------
# API 오류 표시
# --------------------------------------------------
def show_api_error(error, action="AI 요청"):
    """API 오류 유형과 상세 내용을 표시한다."""
    """API 오류의 종류와 상세 내용을 표시한다."""

    st.error(f"{action}에 실패했어.")
    st.caption(f"오류 유형: {type(error).__name__}")

    error_code = getattr(error, "code", None)
    error_message = getattr(error, "message", None)
    error_text = str(error)
    error_status = getattr(error, "status", None)

    if error_code is not None:
        st.caption(f"오류 코드: {error_code}")
    if error_status is None:
        error_status = getattr(error, "code", None)

    if error_status:
        st.caption(f"오류 상태: {error_status}")

    if error_message:
        st.error(f"상세 내용: {error_message}")
    if error_text:
        st.error(f"상세 내용: {error_text}")
    else:
        detail = str(error).strip()
        st.info("상세 오류 메시지를 확인할 수 없어.")

        if detail:
            st.error(f"상세 내용: {detail}")
        else:
            st.info("상세 오류 메시지를 확인할 수 없어.")

# --------------------------------------------------
# 일시적인 오류 확인
# --------------------------------------------------
def is_temporary_error(error):
    """재시도할 가치가 있는 일시적인 오류인지 확인한다."""

    error_text = str(error).upper()

    error_code = getattr(error, "code", None)
    error_status = getattr(error, "status", None)

    error_info = (
        error_text
        + " "
        + str(error_code).upper()
        + " "
        + str(error_status).upper()
    )

    temporary_errors = [
        "503",
        "UNAVAILABLE",
        "HIGH DEMAND",
        "429",
        "RESOURCE_EXHAUSTED",
        "504",
        "502",
        "500",
        "INTERNAL",
    ]

    return any(
        code in error_info
        for code in temporary_errors
    )


# --------------------------------------------------
# Gemini 텍스트 생성 및 자동 재시도
# --------------------------------------------------
def generate_text(prompt, action="AI 요청"):
    """Gemini에 요청하고 생성된 텍스트를 반환한다."""
    """Gemini에 요청하고 일시적인 오류가 발생하면 재시도한다."""

    client, model_name = get_gemini_client()

    if client is None:
        return None

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
    max_attempts = 3
    wait_times = [2, 5]

        answer = getattr(response, "text", None)
    status_box = st.empty()

        if answer and answer.strip():
            return answer.strip()
    for attempt in range(max_attempts):

        st.warning(
            "AI 응답이 비어 있어. "
            "요청 내용을 조금 바꿔서 다시 시도해 줘."
        )
        return None
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

    except Exception as error:
        show_api_error(error, action)
        return None
            answer = getattr(response, "text", None)

            status_box.empty()

            if answer and answer.strip():
                return answer.strip()

            st.warning(
                "AI 응답이 비어 있어. "
                "요청 내용을 조금 바꿔서 다시 시도해 줘."
            )

            return None

        except Exception as error:

            # 일시적인 오류인지 확인
            temporary = is_temporary_error(error)

            # 재시도할 수 없는 오류이거나 마지막 시도라면 종료
            if not temporary or attempt == max_attempts - 1:

                status_box.empty()
                show_api_error(error, action)

                return None

            # 재시도 대기 시간
            wait_seconds = wait_times[attempt]

            status_box.warning(
                f"Gemini 서버가 일시적으로 바빠. "
                f"{wait_seconds}초 후 다시 요청할게. "
                f"({attempt + 1}/{max_attempts - 1}회 재시도)"
            )

            time.sleep(wait_seconds)

    status_box.empty()

    return None


# --------------------------------------------------
@@ -243,6 +329,7 @@ def generate_text(prompt, action="AI 요청"):
    )

    st.divider()

    st.subheader("도안 수정하기")

    # ----------------------------------------------
@@ -256,14 +343,17 @@ def generate_text(prompt, action="AI 요청"):
            key="pattern_revision_input",
        )

        revise = st.form_submit_button("도안 수정 요청")
        revise = st.form_submit_button(
            "도안 수정 요청"
        )

    # ----------------------------------------------
    # 도안 수정 처리
    # ----------------------------------------------
    if revise:

        if not revision.strip():

            st.warning("수정할 내용을 입력해 줘.")

        else:
@@ -295,7 +385,9 @@ def generate_text(prompt, action="AI 요청"):
                )

                if revised_answer:

                    st.session_state["latest_pattern"] = revised_answer

                    st.rerun()
