
import os
import streamlit as st
from google import genai

from common import setup, header, secret


# ==================================================
# 1. 기본 설정
# ==================================================

setup()

header(
    "AI 도안",
    "말로 설명하면, 함께 뜨개 도안을 만들어 줄게."
)

MODEL_NAME = "gemini-3.8-flash"


# ==================================================
# 2. Gemini API 설정
# ==================================================

def get_api_key():
    """common.py의 secret 함수와 환경변수에서 API 키를 가져온다."""

    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        try:
            key = secret(name)
            if key:
                return str(key).strip()
        except Exception:
            pass

    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    """Gemini 클라이언트를 생성한다."""
    return genai.Client(api_key=api_key)


# ==================================================
# 3. AI의 역할 설정
# ==================================================

SYSTEM_INSTRUCTION = """
너는 knit. 앱에서 활동하는 AI 뜨개 전문 도우미야.

사용자와 친근하고 자연스럽게 대화하면서
뜨개질과 관련된 도움을 제공하는 것이 너의 역할이야.

다음 규칙을 지켜줘.

1. 기본적으로 한국어로 대화해.
2. 사용자가 초보자여도 이해할 수 있도록 쉽게 설명해.
3. 대바늘과 코바늘 모두 전문적으로 설명해.
4. 뜨개 작품의 도안, 실 종류, 바늘 크기, 뜨개 기법 등에
   관한 질문에 답변해.
5. 사용자가 원하는 작품을 설명하면 그에 맞는 도안을
   직접 작성해 줘.
6. 도안을 작성할 때는 다음 내용을 포함해 줘.

   - 작품 이름
   - 난이도
   - 준비물
   - 사용 기법 및 약어 설명
   - 뜨는 순서
   - 마무리 방법
   - 주의사항 및 팁

7. 도안은 단계별로 구분하고 코 수와 단 수를 명확하게
   표시해 줘.
8. 작품의 크기나 게이지 등 정확한 정보가 부족하면
   임의로 확정하지 말고 예상값임을 알려줘.
9. 사용자의 요청이 모호해서 정확한 도안을 만들기 어렵다면
   필요한 내용을 자연스럽게 질문해 줘.
10. 이전 대화 내용을 기억하고 앞선 질문과 연결해서 답변해.
11. 불필요하게 긴 설명보다는 사용자가 원하는 내용을
    정확하고 이해하기 쉽게 전달해 줘.

너는 단순한 정보 검색 도구가 아니라
사용자와 함께 뜨개 작품을 고민하고 만드는 AI 파트너야.
"""


# ==================================================
# 4. 대화 초기화
# ==================================================

WELCOME_MESSAGE = (
    "안녕하세요! 🧶\n\n"
    "나는 knit.의 AI 뜨개 도우미야.\n\n"
    "만들고 싶은 작품이 있거나 뜨개질에 관해 궁금한 점이 있다면 "
    "편하게 이야기해 줘!\n\n"
    "작품에 대한 설명만 해 줘도 함께 도안을 만들어 줄게."
)


if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE
        }
    ]


if "last_interaction_id" not in st.session_state:
    st.session_state.last_interaction_id = None


# ==================================================
# 5. 새 대화 버튼
# ==================================================

left, right = st.columns([5, 1])

with right:
    if st.button("새 대화", use_container_width=True):

        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE
            }
        ]

        st.session_state.last_interaction_id = None

        st.rerun()


st.caption("뜨개와 관련된 질문을 자유롭게 입력해 주세요.")


# ==================================================
# 6. 이전 대화 내용 표시
# ==================================================

for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ==================================================
# 7. 사용자 메시지 입력
# ==================================================

prompt = st.chat_input(
    "어떤 작품을 만들고 싶나요?"
)


# ==================================================
# 8. Gemini에게 메시지 전달
# ==================================================

if prompt:

    api_key = get_api_key()

    if not api_key:

        st.error(
            "Gemini API 키를 찾을 수 없어요. "
            "GEMINI_API_KEY 설정을 확인해 주세요."
        )

    else:

        # 사용자 메시지 저장
        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        # 사용자 메시지 화면에 표시
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):

            with st.spinner("답변을 준비하고 있어요..."):

                try:

                    client = get_gemini_client(api_key)

                    # API 요청 내용
                    request = {
                        "model": MODEL_NAME,
                        "input": prompt,
                        "system_instruction": SYSTEM_INSTRUCTION
                    }

                    # 이전 대화가 있다면 대화 ID 전달
                    if st.session_state.last_interaction_id:

                        request["previous_interaction_id"] = (
                            st.session_state.last_interaction_id
                        )

                    # Gemini API 호출
                    response = client.interactions.create(
                        **request
                    )

                    # AI 답변 가져오기
                    answer = response.output_text

                    if not answer:
                        answer = "응답을 생성하지 못했어요. 다시 질문해 주세요."

                    # 최신 대화 ID 저장
                    st.session_state.last_interaction_id = response.id

                    # 화면에 답변 표시
                    st.markdown(answer)

                    # 대화 내용 저장
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                except Exception as e:

                    error_text = str(e)
                    error_upper = error_text.upper()

                    if any(code in error_upper for code in [
                        "503",
                        "UNAVAILABLE",
                        "429",
                        "RESOURCE_EXHAUSTED"
                    ]):

                        error_message = (
                            "Gemini 서버에 요청이 많거나 사용량 한도에 "
                            "도달했어요. 잠시 후 다시 시도해 주세요."
                        )

                    elif any(code in error_upper for code in [
                        "API_KEY_INVALID",
                        "401",
                        "403"
                    ]):

                        error_message = (
                            "API 키 인증에 문제가 있어요. "
                            "GEMINI_API_KEY 설정을 확인해 주세요."
                        )

                    else:

                        error_message = (
                            "답변을 생성하는 중 오류가 발생했어요. "
                            "아래 오류 내용을 확인해 주세요."
                        )

                    st.error(error_message)

                    with st.expander("오류 자세히 보기"):
                        st.code(
                            f"{type(e).__name__}: {error_text}"
                        )

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": f"⚠️ {error_message}"
                        }
                    )




