
import os
import streamlit as st
from google import genai
from google.genai import types

from common import setup, header, secret


# ==================================================
# 1. 기본 설정
# ==================================================
setup()

header(
    "AI 도안",
    "말로 설명하면, 함께 뜨개 도안을 만들어 줄게."
)


# ==================================================
# 2. 세션 상태 초기화
# ==================================================
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                "안녕! 나는 knit.의 AI 도안 도우미야. 🧶\n\n"
                "어떤 뜨개 작품을 만들고 싶어?\n"
                "작품의 종류나 원하는 모양을 편하게 이야기해 줘. "
                "아직 구체적으로 정하지 않아도 괜찮아!"
            )
        }
    ]

if "latest_pattern" not in st.session_state:
    st.session_state["latest_pattern"] = None

if "latest_pattern_title" not in st.session_state:
    st.session_state["latest_pattern_title"] = ""

if "chat_busy" not in st.session_state:
    st.session_state["chat_busy"] = False


# ==================================================
# 3. Gemini API 설정
# ==================================================
def get_gemini_client():

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
            "Gemini API 키를 찾을 수 없어. "
            "Streamlit Secrets를 확인해 줘."
        )
        return None, None

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                api_version="v1"
            )
        )

        return client, model_name

    except Exception as error:
        st.error("Gemini 연결에 실패했어.")
        st.caption(str(error))
        return None, None


# ==================================================
# 4. 오류 확인
# ==================================================
def get_error_info(error):

    return (
        str(error).upper()
        + " "
        + str(getattr(error, "code", "")).upper()
        + " "
        + str(getattr(error, "status", "")).upper()
    )


def show_api_error(error):

    error_info = get_error_info(error)

    st.error("AI 응답을 가져오지 못했어.")

    if "503" in error_info or "UNAVAILABLE" in error_info:
        st.warning(
            "Gemini 서버에 요청이 많아. "
            "잠시 기다렸다가 다시 메시지를 보내 줘."
        )

    elif "429" in error_info or "RESOURCE_EXHAUSTED" in error_info:
        st.warning(
            "API 사용량 제한에 도달했어. "
            "사용량이 회복된 후 다시 시도해 줘."
        )

    elif "404" in error_info or "NOT_FOUND" in error_info:
        st.warning(
            "모델을 찾을 수 없어. "
            "GEMINI_MODEL 설정을 확인해 줘."
        )

    elif "401" in error_info or "UNAUTHENTICATED" in error_info:
        st.warning("API 키를 확인해 줘.")

    elif "403" in error_info or "PERMISSION_DENIED" in error_info:
        st.warning("API 사용 권한을 확인해 줘.")

    elif "TIMEOUT" in error_info or "DEADLINE_EXCEEDED" in error_info:
        st.warning(
            "응답 시간이 너무 길어 요청이 종료됐어. "
            "잠시 후 다시 시도해 줘."
        )

    else:
        st.warning("잠시 후 다시 시도해 줘.")

    st.caption(f"상세 오류: {error}")


# ==================================================
# 5. AI에게 전달할 역할 설정
# ==================================================
SYSTEM_INSTRUCTION = """
너는 knit.이라는 뜨개 커뮤니티의 AI 도안 디자이너야.

사용자와 자연스럽게 대화하면서 원하는 뜨개 작품의
도안을 함께 만들어 주는 역할을 해.

[기본 대화 방식]

1. 처음부터 모든 정보를 한꺼번에 질문하지 마.
2. 사용자의 말을 이해하고 자연스럽게 대화를 이어 가.
3. 한 번에 질문은 1~2개 정도만 해.
4. 사용자가 이미 알려 준 정보는 다시 질문하지 마.
5. 사용자가 뜨개 경험이 적다면 쉬운 말로 설명해.
6. 사용자가 원하는 작품을 구체적으로 정하지 않았다면
   부담 없이 아이디어를 제안해.
7. 사용자의 의견을 무시하고 임의로 작품을 결정하지 마.
8. 한국어로 친절하고 간결하게 답변해.

[도안 제작에 필요한 정보]

대화를 통해 다음 정보를 파악해.

- 작품 종류
- 뜨개 방식 (코바늘 또는 대바늘)
- 완성 크기
- 실의 종류와 굵기
- 바늘 크기
- 게이지
- 사용자의 뜨개 경험
- 원하는 디자인과 추가 요청

모든 정보가 반드시 필요한 것은 아니야.
필요한 정보가 부족하다면 적절한 가정을 밝히고 진행해.

[도안 생성 규칙]

사용자가 도안을 만들어 달라고 요청하면
지금까지의 대화 내용을 바탕으로 전체 도안을 작성해.

도안은 다음 순서로 작성해.

[[PATTERN_START]]

# 도안 제목

## 1. 완성 모습
작품의 모양과 특징

## 2. 준비물
실, 바늘, 기타 준비물

## 3. 시작하기 전 확인
게이지와 기본 뜨개 기법

## 4. 단계별 도안
시작 코, 코 수, 단 수, 작업 순서

## 5. 크기 조절 방법
코 수와 단 수를 조절하는 방법

## 6. 마무리
연결, 실 정리, 형태 잡기

## 7. 주의 사항
실제 작업 시 확인할 점

[[PATTERN_END]]

[정확성 규칙]

- 실제로 가능한 뜨개 작업 순서를 작성해.
- 코바늘과 대바늘의 기법을 혼동하지 마.
- 코 수와 단 수가 서로 맞는지 확인해.
- 게이지가 없으면 정확한 완성 크기를 보장하지 마.
- 불확실한 코 수는 추정치라고 밝혀.
- 초보자에게 어려운 용어는 설명해.
- 기존 출판 도안의 문장을 그대로 복제하지 마.
- 실제 작업 전에 시험편을 권장해.

[도안 수정 규칙]

사용자가 기존 도안의 수정을 요청하면
기존 도안의 중요한 내용은 유지하면서 수정해.

수정된 전체 도안을 다시 작성하고
동일한 [[PATTERN_START]]와 [[PATTERN_END]] 표시를 사용해.

[일반 대화 규칙]

도안 생성 요청이 아니라면
완성 도안을 억지로 작성하지 마.
질문에 답하거나 필요한 정보를 자연스럽게 물어봐.
"""


# ==================================================
# 6. 대화 내용 정리
# ==================================================
def make_chat_context():

    messages = st.session_state["chat_messages"]

    # 최근 대화 12개만 API에 전달
    recent_messages = messages[-12:]

    conversation = []

    for message in recent_messages:

        role = (
            "사용자"
            if message["role"] == "user"
            else "AI 도안 도우미"
        )

        conversation.append(
            f"{role}: {message['content']}"
        )

    return "\n\n".join(conversation)


# ==================================================
# 7. Gemini 응답 생성
# ==================================================
def generate_chat_response():

    client, model_name = get_gemini_client()

    if client is None:
        return None

    context = make_chat_context()

    try:

        response = client.interactions.create(
            model=model_name,
            input=context,
            system_instruction=SYSTEM_INSTRUCTION,
            timeout=90,
            store=False,
        )

        answer = getattr(
            response,
            "output_text",
            None
        )

        if answer and answer.strip():
            return answer.strip()

        st.warning("AI 응답이 비어 있어.")
        return None

    except Exception as error:

        show_api_error(error)
        return None


# ==================================================
# 8. 도안 저장
# ==================================================
def save_pattern(answer):

    start_marker = "[[PATTERN_START]]"
    end_marker = "[[PATTERN_END]]"

    if start_marker not in answer:
        return

    if end_marker not in answer:
        return

    start = answer.find(start_marker) + len(start_marker)
    end = answer.find(end_marker)

    if end <= start:
        return

    pattern = answer[start:end].strip()

    if not pattern:
        return

    st.session_state["latest_pattern"] = pattern

    first_line = pattern.splitlines()[0].strip()

    st.session_state["latest_pattern_title"] = (
        first_line.replace("#", "").strip()
    )


# ==================================================
# 9. 페이지 안내
# ==================================================
st.markdown(
    """
    <div class="knit-card">
        <strong>🧶 AI와 대화하며 도안 만들기</strong><br>
        <span class="knit-muted">
            만들고 싶은 작품을 자유롭게 설명해 줘.
            실이나 바늘을 아직 정하지 못했다면
            AI와 함께 결정해도 좋아.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 10. 대화 초기화 버튼
# ==================================================
col1, col2 = st.columns([4, 1])

with col1:
    st.caption("AI 도안 디자이너와 나눈 대화")

with col2:

    if st.button(
        "새 대화",
        use_container_width=True,
        disabled=st.session_state["chat_busy"],
    ):

        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "새로운 작품을 만들어 보자! 🧶\n\n"
                    "어떤 뜨개 작품을 만들고 싶어?"
                )
            }
        ]

        st.session_state["latest_pattern"] = None
        st.session_state["latest_pattern_title"] = ""

        st.rerun()


st.divider()


# ==================================================
# 11. 채팅 화면
# ==================================================
chat_area = st.container()

with chat_area:

    for message in st.session_state["chat_messages"]:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])


# ==================================================
# 12. 사용자 메시지 입력
# ==================================================
user_input = st.chat_input(
    "만들고 싶은 작품이나 궁금한 점을 입력해 줘...",
    disabled=st.session_state["chat_busy"],
)


# ==================================================
# 13. 사용자 메시지 처리
# ==================================================
if user_input:

    # 사용자 메시지 저장
    st.session_state["chat_messages"].append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    # 사용자 메시지 표시
    with chat_area:

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):

            with st.spinner("답변을 생각하고 있어..."):

                answer = generate_chat_response()

            if answer:

                # 대화 저장
                st.session_state["chat_messages"].append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

                # 완성 도안이 포함되었는지 확인
                save_pattern(answer)

                # 도안 표시 시 마커 제거
                display_answer = (
                    answer
                    .replace("[[PATTERN_START]]", "")
                    .replace("[[PATTERN_END]]", "")
                )

                st.markdown(display_answer)

            else:

                st.session_state["chat_messages"].append(
                    {
                        "role": "assistant",
                        "content": (
                            "지금은 AI 응답을 가져오지 못했어. "
                            "잠시 후 다시 메시지를 보내 줘."
                        )
                    }
                )

                st.warning(
                    "요청에 실패했어. "
                    "이전 대화는 유지되어 있어."
                )


# ==================================================
# 14. 완성된 도안 다운로드
# ==================================================
latest_pattern = st.session_state.get(
    "latest_pattern"
)

if latest_pattern:

    st.divider()

    st.subheader("🧶 완성된 도안")

    st.success(
        st.session_state.get(
            "latest_pattern_title",
            "새로운 뜨개 도안"
        ) + " 도안이 저장되었어!"
    )

    with st.expander("완성된 도안 다시 보기", expanded=True):

        st.markdown(latest_pattern)

    st.download_button(
        "도안 텍스트 저장하기",
        data=latest_pattern,
        file_name="knit_pattern.txt",
        mime="text/plain",
        key="download_pattern",
        use_container_width=True,
    )


# ==================================================
# 15. 하단 안내
# ==================================================
st.divider()

st.caption(
    "AI가 작성한 도안은 초안이야. "
    "실제 작업 전에 게이지와 코 수를 확인해 줘."
)


