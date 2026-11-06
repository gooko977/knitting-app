
import os
import time
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

MODEL_NAME = "gemini-3.8-flash"
MAX_RETRIES = 3


# ==================================================
# 2. AI 역할 설정
# ==================================================

SYSTEM_INSTRUCTION = """
너는 knit. 앱의 AI 뜨개 전문 도우미야.

사용자와 친근하고 자연스럽게 대화하면서
뜨개질과 관련된 도움을 제공하는 것이 역할이야.

[기본 규칙]

1. 기본적으로 한국어로 대화해.
2. 초보자도 이해할 수 있도록 쉽게 설명해.
3. 대바늘과 코바늘 모두 설명해.
4. 뜨개 작품, 도안, 실 종류, 바늘 크기,
   뜨개 기법 등에 관한 질문에 답변해.
5. 사용자가 원하는 작품을 설명하면
   그에 맞는 도안을 작성해.
6. 이전 대화 내용을 참고해서 답변해.
7. 모르는 내용은 사실처럼 추측하지 마.
8. 필요한 정보가 부족하면 사용자에게 질문해.

[도안 작성]

사용자가 도안을 요청하면 다음 내용을 포함해.

- 작품 이름
- 난이도
- 준비물
- 사용 기법
- 뜨는 순서
- 코 수와 단 수
- 마무리 방법
- 주의사항

도안은 단계별로 구분해.
코 수와 단 수가 서로 맞는지 확인해.
크기나 게이지가 정해지지 않았다면
예상값임을 알려줘.

[대화 방식]

친절하고 자연스럽게 대화해.
불필요하게 긴 설명은 피하고,
사용자와 함께 작품을 만드는 AI 파트너처럼 행동해.
"""


# ==================================================
# 3. API 키
# ==================================================

def get_api_key():

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


# ==================================================
# 4. Gemini 클라이언트
# ==================================================

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):

    return genai.Client(api_key=api_key)


# ==================================================
# 5. 오류 확인
# ==================================================

def is_temporary_error(error):

    error_text = str(error).upper()

    temporary_codes = [
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "504",
        "DEADLINE_EXCEEDED",
        "TIMEOUT"
    ]

    return any(
        code in error_text
        for code in temporary_codes
    )


def get_error_message(error):

    error_text = str(error).upper()

    if "503" in error_text or "UNAVAILABLE" in error_text:
        return "Gemini 서버에 요청이 많아요. 잠시 후 다시 시도해 주세요."

    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
        return "API 사용량 한도에 도달했어요. 잠시 후 다시 시도해 주세요."

    if "401" in error_text or "403" in error_text:
        return "API 키 인증에 문제가 있어요. API 키 설정을 확인해 주세요."

    if "404" in error_text or "NOT_FOUND" in error_text:
        return "요청한 모델을 찾을 수 없어요. 모델 이름을 확인해 주세요."

    return "답변을 생성하는 중 문제가 발생했어요."


# ==================================================
# 6. Gemini 응답 생성
# ==================================================

def generate_response(client, history, prompt):

    # 이전 대화 내용을 Gemini 입력 형식으로 변환
    contents = []

    for message in history:

        contents.append(
            types.Content(
                role=message["role"],
                parts=[
                    types.Part.from_text(
                        text=message["content"]
                    )
                ]
            )
        )

    # 현재 사용자 메시지 추가
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=prompt
                )
            ]
        )
    )

    last_error = None

    # 서버 오류 재시도
    for attempt in range(MAX_RETRIES):

        try:

            response = client.models.generate_content(

                model=MODEL_NAME,

                contents=contents,

                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )

            )

            answer = response.text

            if not answer:
                raise ValueError("AI가 빈 답변을 반환했어요.")

            return answer

        except Exception as e:

            last_error = e

            if is_temporary_error(e):

                if attempt < MAX_RETRIES - 1:

                    wait_time = 2 ** (attempt + 1)

                    time.sleep(wait_time)

                    continue

            raise last_error

    raise last_error


# ==================================================
# 7. 세션 상태 초기화
# ==================================================

WELCOME_MESSAGE = """
안녕하세요! 🧶

나는 knit.의 AI 뜨개 도우미야.

만들고 싶은 작품이 있거나
뜨개질에 관해 궁금한 점이 있다면
편하게 이야기해 줘!

작품에 대한 설명만 해 줘도
함께 도안을 만들어 줄게.
"""


if "chat_history" not in st.session_state:

    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE
        }
    ]


if "api_history" not in st.session_state:

    st.session_state.api_history = []


# ==================================================
# 8. 새 대화
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

        st.session_state.api_history = []

        st.rerun()


st.caption("뜨개와 관련된 질문을 자유롭게 입력해 주세요.")


# ==================================================
# 9. 이전 대화 표시
# ==================================================

for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ==================================================
# 10. 사용자 메시지 입력
# ==================================================

prompt = st.chat_input(
    "어떤 작품을 만들고 싶나요?"
)


# ==================================================
# 11. 메시지 처리
# ==================================================

if prompt:

    api_key = get_api_key()

    if not api_key:

        st.error(
            "Gemini API 키를 찾을 수 없어요. "
            "secrets.toml 설정을 확인해 주세요."
        )

    else:

        # 사용자 메시지 표시
        with st.chat_message("user"):

            st.markdown(prompt)

        # Gemini 클라이언트 생성
        client = get_gemini_client(api_key)

        # AI 답변 생성
        with st.chat_message("assistant"):

            with st.spinner(
                "뜨개 도우미가 답변을 준비하고 있어요..."
            ):

                try:

                    answer = generate_response(

                        client,

                        st.session_state.api_history,

                        prompt

                    )

                    # AI 답변 표시
                    st.markdown(answer)

                    # 성공한 경우에만 대화 기록 저장
                    st.session_state.api_history.extend([

                        {
                            "role": "user",
                            "content": prompt
                        },

                        {
                            "role": "model",
                            "content": answer
                        }

                    ])

                    st.session_state.chat_history.extend([

                        {
                            "role": "user",
                            "content": prompt
                        },

                        {
                            "role": "assistant",
                            "content": answer
                        }

                    ])

                except Exception as e:

                    error_message = get_error_message(e)

                    st.error(error_message)

                    with st.expander("오류 자세히 보기"):

                        st.code(
                            f"{type(e).__name__}: {e}"
                        )

                    st.info(
                        "메시지가 처리되지 않았어요. "
                        "잠시 후 다시 입력해 주세요."
                    )
