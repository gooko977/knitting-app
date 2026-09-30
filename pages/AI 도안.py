"""knit. - AI 도안 화면 (챗봇 + 내 게이지 입력)"""
import json
import re
import xml.etree.ElementTree as ET

import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

from common import check_text, header, secret, setup

setup()  # 반드시 맨 처음

# =====================================================================
# 4. 도안 챗봇 (+ 내 게이지 입력)
# =====================================================================

# 모델 이름은 바뀔 수 있어서, Secrets에 GEMINI_MODEL을 넣으면 그걸 쓰고
# 없으면 아래 후보를 위에서부터 차례로 시도해요 (없는 모델이면 다음 후보로).
MODELS = [secret("GEMINI_MODEL")] if secret("GEMINI_MODEL") else [
    "gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash"]
MAX_CALLS = 15  # 한 세션에서 도안을 만들 수 있는 최대 횟수 (API 비용 보호)

GUIDE = """한국 뜨개 호수 참고표:
코바늘: 2/0호=2.0mm, 3/0호=2.3mm, 4/0호=2.5mm, 5/0호=3.0mm, 6/0호=3.5mm, 7/0호=4.0mm, 8/0호=5.0mm, 10/0호=6.0mm
대바늘: 0호=2.1mm, 1호=2.4mm, 2호=2.7mm, 3호=3.0mm, 4호=3.3mm, 5호=3.6mm, 6호=3.9mm, 7호=4.2mm, 8호=4.5mm, 10호=5.1mm, 12호=5.7mm, 15호=6.9mm"""


@st.cache_resource
def get_client():
    key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("NO_KEY")
    return genai.Client(api_key=key)


def build_system(tool, level, out, gauge=None):
    crochet = tool == "코바늘"
    want = {"이미지+도안": "이미지와 도안", "이미지만": "이미지만", "도안만": "도안만"}[out]
    svg_rule = (
        "빈 문자열"
        if out == "도안만"
        else '완성된 모습을 깔끔한 플랫 일러스트로 그린 SVG 문자열. <svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">로 시작, '
        "둥근 도형과 점선 스티치로 실 질감 표현, script/image 금지, 3KB 이하"
    )
    # 케이블/바늘 길이는 JSON에서도 맨 마지막(svg 바로 앞)에 둔다
    cable = "" if crochet else '  "cable": "줄바늘이면 케이블 길이(예: 80cm), 막대바늘이면 막대바늘 길이를 작품에 맞게 추천",\n'
    tool_ex = "코바늘 호수 (예: 5/0호 (3.0mm))" if crochet else "대바늘 호수 (예: 5호 (3.6mm))"
    stitches = "사슬, 짧은뜨기, 긴뜨기 등" if crochet else "겉뜨기, 안뜨기, 코잡기, 코막음 등"

    if gauge:
        extra = ""
        if gauge.get("yarn"):
            extra += f", 사용할 실: {gauge['yarn']}"
        if gauge.get("needle"):
            extra += f", 스와치를 뜬 바늘: {gauge['needle']}"
        gauge_rule = (
            f"\n[사용자 게이지] 사용자가 직접 뜬 10cm x 10cm 스와치 결과: 가로 {gauge['st']}코 x 세로 {gauge['rows']}단{extra}.\n"
            "이 게이지를 최우선 기준으로 삼아 도안의 모든 코수·단수를 다시 계산해.\n"
            "- 코수 = 가로 cm x (가로 코수 / 10), 단수 = 세로 cm x (세로 단수 / 10)\n"
            "- 무늬 반복 단위가 있으면 가장 가까운 배수로 맞춰.\n"
            '- "gauge" 필드에는 사용자가 입력한 값을 그대로 쓰고, 바늘 호수가 이 실과 게이지에 어울리는지 tip에 한 문장으로 알려줘.\n'
        )
    else:
        gauge_rule = "\n게이지는 일반적인 값으로 추정하고, 사용자가 실을 정하면 10cm x 10cm 스와치를 떠서 게이지를 알려달라고 tip에서 권해줘.\n"

    return f"""너는 친절한 한국어 뜨개질 도안 선생님이야. 사용자는 뜨개질을 좋아하는 고등학생이야.
선택 옵션: 바늘={tool}, 난이도={level}, 결과물={want}.
{GUIDE}
{gauge_rule}
반드시 JSON 객체 하나만 출력해. 코드펜스나 설명 문장은 금지. 형식:
{{
  "reply": "짧은 한마디",
  "title": "작품 이름",
  "size": "완성 크기",
  "yarn": "추천 실(굵기·소재·색·대략 g)",
  "tool": "{tool_ex}",
  "gauge": "10cm 기준 코수 x 단수",
  "other": "필요한 부자재",
  "steps": ["도안 6~12단계. 코수/단수를 구체적으로 ({stitches})"],
  "tip": "초보를 위한 팁 1~2문장",
{cable}  "svg": "{svg_rule}"
}}"""


def clean_svg(code):
    """SVG에서 위험한 태그/속성 제거."""
    try:
        code = re.sub(r"^<\?xml[^>]*\?>", "", code.strip())
        root = ET.fromstring(code)
    except ET.ParseError:
        return ""
    bad = {"script", "foreignobject", "image", "use", "a"}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split("}")[-1].lower() in bad:
                parent.remove(child)
    for el in root.iter():
        for k in list(el.attrib):
            if k.lower().startswith("on") or "javascript:" in el.attrib[k].lower():
                del el.attrib[k]
    root.set("viewBox", "0 0 300 300")
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    return ET.tostring(root, encoding="unicode")


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def ask(messages, system):
    client = get_client()
    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user",
                      parts=[types.Part(text=m["content"])])
        for m in messages
    ]
    config = types.GenerateContentConfig(
        system_instruction=system, response_mime_type="application/json", max_output_tokens=8192)
    known = st.session_state.get("gemini_model")
    last = None
    for name in ([known] if known else MODELS):
        try:
            resp = client.models.generate_content(model=name, contents=contents, config=config)
            st.session_state["gemini_model"] = name  # 잘 되는 모델은 기억
            return resp.text or ""
        except Exception as e:
            last = e
            if "404" in str(e) or "NOT_FOUND" in str(e):
                st.session_state.pop("gemini_model", None)
                continue  # 이 모델 이름이 없으면 다음 후보로
            raise
    raise last


def explain_error(e):
    """오류 원인을 초보도 알 수 있는 말로 바꿔준다."""
    m = str(e)
    if not (secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")):
        return "Secrets에 GEMINI_API_KEY가 없어요. Streamlit Cloud의 Settings → Secrets를 확인해 주세요."
    if any(w in m for w in ("API_KEY_INVALID", "API key not valid", "UNAUTHENTICATED", "401")):
        return "API 키가 올바르지 않아요. AI Studio에서 키를 다시 복사해 Secrets에 넣어 주세요."
    if "403" in m or "PERMISSION_DENIED" in m:
        return "이 키로는 사용할 수 없대요(권한 오류). AI Studio에서 새 키를 만들어 넣어 보세요."
    if "429" in m or "RESOURCE_EXHAUSTED" in m:
        return "사용 한도를 넘었어요. 잠시 후 다시 시도해 주세요."
    if "404" in m or "NOT_FOUND" in m:
        return "모델 이름을 찾지 못했어요. Secrets에 GEMINI_MODEL = \"모델이름\"을 넣어 주세요."
    if isinstance(e, ValueError):  # JSON 해석 실패
        return "도안 형식이 깨졌어요. 다시 한 번 시도해 주세요."
    return "결과를 만들지 못했어요. 잠시 후 다시 시도해 주세요."


def show_result(r, tool, out):
    st.subheader(r.get("title", "작품"))
    svg = clean_svg(r.get("svg", "")) if r.get("svg") else ""
    if svg:
        components.html(
            f'<div style="background:#F3EFE9;border:1px solid #E7E2DB;border-radius:12px;padding:8px;text-align:center">'
            f'<div style="max-width:340px;margin:auto">{svg}</div></div>',
            height=360,
        )
    st.markdown("**준비물**")
    cols = st.columns(2)
    items = [
        ("사이즈", r.get("size")),
        ("실", r.get("yarn")),
        ("코바늘 호수" if tool == "코바늘" else "대바늘 호수", r.get("tool")),
        ("게이지 (10cm 기준)", r.get("gauge")),
        ("부자재", r.get("other")),
    ]
    for i, it in enumerate([x for x in items if x and x[1]]):
        cols[i % 2].info(f"**{it[0]}**\n\n{it[1]}")
    if r.get("steps"):
        st.markdown("**도안**" if out != "이미지만" else "**만드는 순서 요약**")
        for i, s in enumerate(r["steps"], 1):
            st.markdown(f"{i}. {s}")
    if r.get("tip"):
        st.caption(f"팁 · {r['tip']}")
    # 케이블/바늘 길이는 맨 마지막에 알려준다
    if tool == "대바늘" and r.get("cable"):
        st.info(f"**케이블/바늘 길이**\n\n{r['cable']}")
    st.caption("※ AI가 만든 그림과 도안이라 실제와 다를 수 있어요. 작은 조각으로 게이지를 먼저 떠보세요!")


def generate(user_text, tool, level, out):
    """사용자 메시지를 기록하고 도안을 만들어 화면과 대화 기록에 추가."""
    chat = st.session_state.chat
    if st.session_state.n_calls >= MAX_CALLS:
        st.warning("오늘은 여기까지! 도안 만들기 횟수를 다 썼어요. 나중에 다시 만들어 봐요.")
        return
    st.session_state.n_calls += 1

    chat.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    # API에는 최근 대화만 전달 (이전 도안은 핵심 정보만 요약)
    api_msgs = []
    for m in chat[-7:]:
        if m["role"] == "user":
            api_msgs.append({"role": "user", "content": m["content"]})
        else:
            r = m["result"]
            summary = json.dumps(
                {k: r.get(k) for k in ("title", "size", "yarn", "tool", "gauge", "steps")}, ensure_ascii=False
            )
            api_msgs.append({"role": "assistant", "content": summary})
    while api_msgs and api_msgs[0]["role"] == "assistant":
        api_msgs.pop(0)

    system = build_system(tool, level, out, st.session_state.get("gauge"))
    with st.chat_message("assistant"):
        result, err = None, None
        with st.spinner("도안을 만드는 중..."):
            for _ in range(2):  # JSON이 깨지면 한 번 더 시도
                try:
                    result = parse_json(ask(api_msgs, system))
                    break
                except Exception as e:
                    err = e
        if result is None:
            st.error(explain_error(err))
            if secret("DEBUG"):
                st.exception(err)
            chat.pop()  # 실패한 질문은 기록에서 뺀다
            return
        st.write(result.get("reply", ""))
        show_result(result, tool, out)
    chat.append({"role": "assistant", "content": "", "result": result, "tool": tool, "out": out})


def gauge_panel():
    """마지막 도안 아래에 10cm x 10cm 게이지 입력 칸을 보여준다."""
    chat = st.session_state.chat
    if not chat or chat[-1]["role"] != "assistant":
        return
    last = chat[-1]["result"]
    g = st.session_state.get("gauge")
    n = len(chat)
    label = ("내 게이지 넣기 (10cm × 10cm)" if not g
             else f"내 게이지: 가로 {g['st']}코 × 세로 {g['rows']}단 (수정하기)")
    with st.expander(label, expanded=False):
        st.caption("실이 정해졌다면, 그 실과 바늘로 10cm × 10cm 정도 떠 보세요. "
                   "가로로 몇 코, 세로로 몇 단인지 세어서 적으면 도안의 코수·단수를 내 손 게이지에 맞춰 다시 계산해요.")
        with st.form(f"gauge_form_{n}"):
            yarn = st.text_input("사용할 실", value=((g or {}).get("yarn") or last.get("yarn") or "")[:100],
                                 max_chars=100, key=f"g_yarn_{n}")
            needle = st.text_input("스와치를 뜬 바늘 (선택)", value=(g or {}).get("needle", ""),
                                   max_chars=30, placeholder="예: 5/0호 또는 대바늘 5호", key=f"g_needle_{n}")
            c1, c2 = st.columns(2)
            stitches = c1.number_input("가로 10cm 안의 코수", min_value=4, max_value=60,
                                       value=(g or {}).get("st", 18), step=1, key=f"g_st_{n}")
            rows = c2.number_input("세로 10cm 안의 단수", min_value=4, max_value=80,
                                   value=(g or {}).get("rows", 24), step=1, key=f"g_rows_{n}")
            if st.form_submit_button("이 게이지로 도안 다시 계산"):
                msg = check_text(yarn, needle)
                if msg:
                    st.warning(msg)
                else:
                    st.session_state.gauge = {"yarn": yarn.strip(), "needle": needle.strip(),
                                              "st": int(stitches), "rows": int(rows)}
                    who = f"실은 {yarn.strip()}(으)로 정했어. " if yarn.strip() else ""
                    st.session_state.pending = (
                        f"{who}10cm × 10cm 스와치 게이지가 가로 {int(stitches)}코, 세로 {int(rows)}단이야. "
                        "이 게이지에 맞게 코수와 단수를 다시 계산해서 도안을 고쳐줘."
                    )
                    st.rerun()


def page_chat():
    header("AI 도안", "만들고 싶은 걸 말해주면 완성 이미지와 도안을 그려줄게요!")
    with st.sidebar:
        st.header("옵션")
        tool = st.radio("바늘 종류", ["코바늘", "대바늘"], horizontal=True)
        out = st.radio("결과물", ["이미지+도안", "이미지만", "도안만"])
        level = st.select_slider("난이도", ["초보", "중급", "고급"])
        g = st.session_state.get("gauge")
        if g:
            st.caption(f"적용 중인 게이지: 가로 {g['st']}코 × 세로 {g['rows']}단 (10cm)")
            if st.button("게이지 해제"):
                st.session_state.pop("gauge", None)
                st.rerun()
        if st.button("대화 초기화"):
            for k in ("chat", "gauge", "pending"):
                st.session_state.pop(k, None)
            st.rerun()

    st.session_state.setdefault("chat", [])  # {"role","content","result","tool","out"}
    st.session_state.setdefault("n_calls", 0)

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.write(m["content"])
            else:
                st.write(m["result"].get("reply", ""))
                show_result(m["result"], m["tool"], m["out"])

    prompt = st.chat_input("예) 민트색 코바늘 버킷햇, 리본 달린 걸로")
    pending = st.session_state.pop("pending", None)  # 게이지 입력 버튼에서 온 요청
    text_in = prompt or pending
    if text_in:
        generate(text_in, tool, level, out)

    gauge_panel()


page_chat()
