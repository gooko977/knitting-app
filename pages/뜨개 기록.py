
# pages/뜨개 기록.py

import json
from datetime import date

import streamlit as st
from sqlalchemy import text

from common import (
    setup,
    header,
    q,
    ex,
    engine,
    now,
    esc,
    init_record_options_once,
    get_record_options,
    add_record_option,
    rename_record_option,
    delete_record_option,
)


# ==================================================
# 페이지 초기화
# ==================================================

setup()
init_record_options_once()

nick = st.session_state.get("nick", "뜨개러")

header(
    "🧶 나의 뜨개 기록장",
    "작품마다 도안, 실, 바늘, 게이지와 작업 과정을 정리해.",
)


# ==================================================
# 기본 옵션
# ==================================================

DEFAULT_OPTIONS = {
    "종류": [
        "의류", "가방", "소품", "인형", "홈데코", "기타"
    ],
    "상태": [
        "예정", "진행 중", "완성", "보류"
    ],
    "실 종류": [
        "울", "면", "아크릴", "혼방", "모헤어", "기타"
    ],
    "실 색상": [
        "크림", "베이지", "핑크", "브라운", "그레이", "기타"
    ],
    "바늘 종류": [
        "대바늘", "코바늘", "아프간바늘", "기타"
    ],
}

# 작품 상세 페이지에 기본적으로 표시할 속성
BASE_PROPERTIES = [
    ("종류", "선택"),
    ("상태", "선택"),
    ("완성일", "날짜"),
    ("도안", "텍스트"),
    ("바늘 종류", "선택"),
    ("실 정보", "텍스트"),
    ("실 종류", "선택"),
    ("실 색상", "선택"),
    ("바늘", "텍스트"),
    ("원작게이지", "텍스트"),
    ("세탁 전 게이지", "텍스트"),
    ("세탁 후 게이지", "텍스트"),
    ("사이즈", "텍스트"),
    ("무게", "텍스트"),
]

PROPERTY_TYPES = [
    "텍스트", "숫자", "날짜", "선택", "체크박스"
]


# ==================================================
# 데이터 조회 함수
# ==================================================

def get_my_records():
    return q(
        """
        SELECT id, nick, record_date, project, content, created_at
        FROM records
        WHERE nick = :nick
        ORDER BY id DESC
        """,
        {"nick": nick},
    )


def get_properties(record_id):
    return q(
        """
        SELECT id, record_id, nick, name, kind, value, options, position
        FROM record_properties
        WHERE record_id = :record_id
          AND nick = :nick
        ORDER BY position, id
        """,
        {
            "record_id": record_id,
            "nick": nick,
        },
    )


def get_property_value(record_id, name, default=""):
    rows = q(
        """
        SELECT value
        FROM record_properties
        WHERE record_id = :record_id
          AND nick = :nick
          AND name = :name
        LIMIT 1
        """,
        {
            "record_id": record_id,
            "nick": nick,
            "name": name,
        },
    )

    return rows[0]["value"] if rows else default


def save_property(record_id, name, kind, value, options=None):
    """속성이 있으면 수정하고, 없으면 새로 저장한다."""
    existing = q(
        """
        SELECT id
        FROM record_properties
        WHERE record_id = :record_id
          AND nick = :nick
          AND name = :name
        LIMIT 1
        """,
        {
            "record_id": record_id,
            "nick": nick,
            "name": name,
        },
    )

    options_json = (
        json.dumps(options, ensure_ascii=False)
        if options is not None else None
    )

    if existing:
        ex(
            """
            UPDATE record_properties
            SET kind = :kind,
                value = :value,
                options = :options
            WHERE id = :id AND nick = :nick
            """,
            {
                "kind": kind,
                "value": value,
                "options": options_json,
                "id": existing[0]["id"],
                "nick": nick,
            },
        )
    else:
        ex(
            """
            INSERT INTO record_properties
                (record_id, nick, name, kind, value, options, position)
            VALUES
                (:record_id, :nick, :name, :kind, :value, :options,
                 (SELECT COALESCE(MAX(position), 0) + 1
                  FROM record_properties
                  WHERE record_id = :record_id
                    AND nick = :nick))
            """,
            {
                "record_id": record_id,
                "nick": nick,
                "name": name,
                "kind": kind,
                "value": value,
                "options": options_json,
            },
        )


def remove_property(record_id, property_id):
    ex(
        """
        DELETE FROM record_properties
        WHERE id = :id
          AND record_id = :record_id
          AND nick = :nick
        """,
        {
            "id": property_id,
            "record_id": record_id,
            "nick": nick,
        },
    )


def ensure_default_properties(record_id):
    """기본 속성이 없는 작품에 기본 항목을 준비한다."""
    existing = {
        row["name"]
        for row in get_properties(record_id)
    }

    for position, (name, kind) in enumerate(BASE_PROPERTIES):
        if name not in existing:
            ex(
                """
                INSERT INTO record_properties
                    (record_id, nick, name, kind, value, options, position)
                VALUES
                    (:record_id, :nick, :name, :kind, NULL, NULL, :position)
                """,
                {
                    "record_id": record_id,
                    "nick": nick,
                    "name": name,
                    "kind": kind,
                    "position": position,
                },
            )


# ==================================================
# 옵션 관리 화면
# ==================================================

with st.expander("⚙️ 선택 항목 관리", expanded=False):
    st.caption(
        "종류나 상태 같은 선택 속성에 사용할 항목을 추가하거나 관리할 수 있어."
    )

    option_category = st.selectbox(
        "관리할 항목",
        list(DEFAULT_OPTIONS.keys()),
        key="option_category",
    )

    current_options = get_record_options(
        nick,
        option_category,
        DEFAULT_OPTIONS.get(option_category, []),
    )

    st.write("현재 선택 항목")

    for index, option in enumerate(current_options):
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(option)

        with col2:
            with st.popover("이름 변경"):
                new_name = st.text_input(
                    "새 이름",
                    value=option,
                    key=f"rename_{option_category}_{index}",
                )

                if st.button(
                    "변경 저장",
                    key=f"save_rename_{option_category}_{index}",
                ):
                    if new_name.strip() == option:
                        st.info("변경된 내용이 없어.")
                    elif not new_name.strip():
                        st.warning("이름을 입력해 줘.")
                    elif rename_record_option(
                        nick,
                        option_category,
                        option,
                        new_name.strip(),
                    ):
                        st.success("이름을 변경했어.")
                        st.rerun()
                    elif option in DEFAULT_OPTIONS.get(option_category, []):
                        st.warning(
                            "기본 항목은 직접 변경할 수 없어. "
                            "새 항목을 추가해서 사용해 줘."
                        )
                    else:
                        st.error(
                            "변경에 실패했어. 같은 이름이 이미 있는지 확인해 줘."
                        )

        with col3:
            if option not in DEFAULT_OPTIONS.get(option_category, []):
                if st.button(
                    "삭제",
                    key=f"delete_option_{option_category}_{index}",
                ):
                    if delete_record_option(
                        nick,
                        option_category,
                        option,
                    ):
                        st.success("옵션을 삭제했어.")
                        st.rerun()
                    else:
                        st.error("옵션을 삭제하지 못했어.")

    with st.form("add_record_option_form"):
        new_option = st.text_input(
            "새 선택 항목",
            placeholder="예: 알파카",
        )

        add_option = st.form_submit_button("＋ 항목 추가")

    if add_option:
        value = new_option.strip()

        if not value:
            st.warning("추가할 이름을 입력해 줘.")
        elif value in current_options:
            st.warning("이미 있는 항목이야.")
        elif add_record_option(nick, option_category, value):
            st.success("선택 항목을 추가했어.")
            st.rerun()
        else:
            st.error("항목 추가에 실패했어.")


# ==================================================
# 새 작품 등록
# ==================================================

if "record_mode" not in st.session_state:
    st.session_state.record_mode = "list"

if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None

top_left, top_right = st.columns([3, 1])

with top_left:
    st.markdown("### 나의 작품")

with top_right:
    if st.button(
        "＋ 새 작품 기록하기",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.record_mode = "create"
        st.session_state.selected_project_id = None
        st.rerun()


if st.session_state.record_mode == "create":
    with st.container(border=True):
        st.subheader("새 작품 등록")

        with st.form("create_project_form"):
            project_name = st.text_input(
                "작품 이름 *",
                placeholder="예: 밀키웨이 가디건",
                max_chars=80,
            )

            record_date = st.date_input(
                "시작일",
                value=date.today(),
            )

            memo = st.text_area(
                "작업 메모",
                placeholder="만들게 된 계기나 기억할 내용을 적어 줘.",
                max_chars=5000,
            )

            save_project = st.form_submit_button(
                "작품 만들기",
                type="primary",
                use_container_width=True,
            )

        if save_project:
            project_name = project_name.strip()

            if not project_name:
                st.warning("작품 이름을 입력해 줘.")
            else:
                try:
                    with engine.begin() as conn:
                        result = conn.execute(
                            text("""
                                INSERT INTO records
                                    (nick, record_date, project, content, created_at)
                                VALUES
                                    (:nick, :record_date, :project, :content, :created_at)
                            """),
                            {
                                "nick": nick,
                                "record_date": record_date.isoformat(),
                                "project": project_name,
                                "content": memo.strip(),
                                "created_at": now(),
                            },
                        )

                        new_id = result.lastrowid

                        # PostgreSQL에서는 lastrowid가 없을 수 있으므로
                        # 방금 생성한 작품을 닉네임과 이름으로 다시 조회한다.
                        if new_id is None:
                            row = conn.execute(
                                text("""
                                    SELECT id
                                    FROM records
                                    WHERE nick = :nick
                                      AND project = :project
                                    ORDER BY id DESC
                                    LIMIT 1
                                """),
                                {
                                    "nick": nick,
                                    "project": project_name,
                                },
                            ).first()

                            new_id = row[0] if row else None

                    if new_id is not None:
                        ensure_default_properties(new_id)
                        st.session_state.selected_project_id = new_id
                        st.session_state.record_mode = "detail"
                        st.success("새 작품을 등록했어.")
                        st.rerun()
                    else:
                        st.error("작품은 저장했지만 상세 화면을 열지 못했어.")

                except Exception as error:
                    st.error("작품을 저장하지 못했어.")
                    st.caption(str(error))

        if st.button("취소", key="cancel_create"):
            st.session_state.record_mode = "list"
            st.rerun()


# ==================================================
# 작품 상세 화면
# ==================================================

elif st.session_state.record_mode == "detail":
    project_id = st.session_state.selected_project_id

    selected_rows = q(
        """
        SELECT *
        FROM records
        WHERE id = :id AND nick = :nick
        LIMIT 1
        """,
        {"id": project_id, "nick": nick},
    )

    if not selected_rows:
        st.warning("작품을 찾을 수 없어. 목록에서 다시 선택해 줘.")
        st.session_state.record_mode = "list"
        st.rerun()

    record = selected_rows[0]
    ensure_default_properties(project_id)

    st.button(
        "← 작품 목록으로",
        on_click=lambda: st.session_state.update(
            record_mode="list",
            selected_project_id=None,
        ),
    )

    st.title(f"🧶 {record['project']}")
    st.caption(f"시작일: {record['record_date']}")

    with st.expander("✏️ 작품 이름과 메모 수정"):
        with st.form(f"edit_project_{project_id}"):
            edited_name = st.text_input(
                "작품 이름",
                value=record["project"],
                max_chars=80,
            )

            edited_date = st.date_input(
                "시작일",
                value=date.fromisoformat(record["record_date"]),
            )

            edited_memo = st.text_area(
                "작업 메모",
                value=record["content"] or "",
                max_chars=5000,
            )

            save_basic = st.form_submit_button("기본 정보 저장")

        if save_basic:
            if not edited_name.strip():
                st.warning("작품 이름을 입력해 줘.")
            else:
                ex(
                    """
                    UPDATE records
                    SET project = :project,
                        record_date = :record_date,
                        content = :content
                    WHERE id = :id AND nick = :nick
                    """,
                    {
                        "project": edited_name.strip(),
                        "record_date": edited_date.isoformat(),
                        "content": edited_memo.strip(),
                        "id": project_id,
                        "nick": nick,
                    },
                )
                st.success("작품 정보를 저장했어.")
                st.rerun()

    st.divider()
    st.subheader("작품 속성")
    st.caption(
        "각 항목의 값을 수정하고, 필요한 속성을 추가할 수 있어."
    )

    # 기본 속성 및 사용자 지정 속성 표시
    properties = get_properties(project_id)

    for prop in properties:
        with st.container(border=True):
            left, right = st.columns([1, 2])

            with left:
                st.markdown(f"**{esc(prop['name'])}**")
                st.caption(prop["kind"])

            with right:
                key = f"value_{project_id}_{prop['id']}"
                value = prop.get("value") or ""
                kind = prop["kind"]

                if kind == "선택":
                    defaults = DEFAULT_OPTIONS.get(prop["name"], [])
                    options = get_record_options(
                        nick,
                        prop["name"],
                        defaults,
                    )

                    if value and value not in options:
                        options = [value] + options

                    options = ["선택 안 함"] + options

                    selected_index = (
                        options.index(value)
                        if value in options
                        else 0
                    )

                    new_value = st.selectbox(
                        "값",
                        options,
                        index=selected_index,
                        key=key,
                        label_visibility="collapsed",
                    )

                    if new_value == "선택 안 함":
                        new_value = ""

                elif kind == "날짜":
                    if value:
                        try:
                            date_value = date.fromisoformat(value)
                        except ValueError:
                            date_value = date.today()
                    else:
                        date_value = date.today()

                    use_date = st.checkbox(
                        "날짜 입력",
                        value=bool(value),
                        key=f"use_{key}",
                    )

                    if use_date:
                        new_value = st.date_input(
                            "날짜",
                            value=date_value,
                            key=key,
                            label_visibility="collapsed",
                        ).isoformat()
                    else:
                        new_value = ""

                elif kind == "숫자":
                    new_value = st.text_input(
                        "값",
                        value=value,
                        key=key,
                        placeholder="숫자 입력",
                        label_visibility="collapsed",
                    )

                elif kind == "체크박스":
                    new_value = (
                        "예"
                        if st.checkbox(
                            "완료",
                            value=value == "예",
                            key=key,
                        )
                        else "아니요"
                    )

                else:
                    new_value = st.text_input(
                        "값",
                        value=value,
                        key=key,
                        placeholder="비어 있음",
                        label_visibility="collapsed",
                    )

            if st.button(
                "저장",
                key=f"save_{project_id}_{prop['id']}",
            ):
                if kind == "숫자" and new_value:
                    try:
                        float(new_value)
                    except ValueError:
                        st.warning("숫자를 입력해 줘.")
                        st.stop()

                save_property(
                    project_id,
                    prop["name"],
                    prop["kind"],
                    str(new_value).strip() or None,
                )
                st.success(f"{prop['name']} 속성을 저장했어.")
                st.rerun()

            if prop["name"] not in dict(BASE_PROPERTIES):
                if st.button(
                    "속성 삭제",
                    key=f"remove_{project_id}_{prop['id']}",
                ):
                    remove_property(project_id, prop["id"])
                    st.rerun()

    # --------------------------------------------------
    # 사용자 지정 속성 추가
    # --------------------------------------------------

    with st.expander("＋ 속성 추가", expanded=False):
        with st.form(f"add_property_{project_id}"):
            new_name = st.text_input(
                "속성 이름",
                placeholder="예: 세탁 방법",
                max_chars=100,
            )

            new_kind = st.selectbox(
                "속성 유형",
                PROPERTY_TYPES,
            )

            new_options_text = ""

            if new_kind == "선택":
                new_options_text = st.text_input(
                    "선택 항목",
                    placeholder="예: 손세탁, 세탁기, 드라이클리닝",
                    help="쉼표로 구분해 줘.",
                )

            add_property_button = st.form_submit_button(
                "속성 만들기",
                type="primary",
                use_container_width=True,
            )

        if add_property_button:
            clean_name = new_name.strip()
            existing_names = {
                item["name"]
                for item in get_properties(project_id)
            }

            if not clean_name:
                st.warning("속성 이름을 입력해 줘.")
            elif clean_name in existing_names:
                st.warning("이미 존재하는 속성이야.")
            else:
                custom_options = None

                if new_kind == "선택":
                    custom_options = [
                        item.strip()
                        for item in new_options_text.split(",")
                        if item.strip()
                    ]

                    if not custom_options:
                        st.warning("선택 항목을 하나 이상 입력해 줘.")
                        st.stop()

                save_property(
                    project_id,
                    clean_name,
                    new_kind,
                    None,
                    custom_options,
                )
                st.success("새 속성을 추가했어.")
                st.rerun()

    st.divider()

    with st.expander("🗑️ 작품 삭제"):
        st.warning("삭제한 작품과 해당 작품의 속성은 복구할 수 없어.")

        confirm_delete = st.checkbox(
            "이 작품을 삭제하겠습니다.",
            key=f"confirm_delete_{project_id}",
        )

        if st.button(
            "작품 영구 삭제",
            disabled=not confirm_delete,
            key=f"delete_project_{project_id}",
        ):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        DELETE FROM record_properties
                        WHERE record_id = :id AND nick = :nick
                    """),
                    {"id": project_id, "nick": nick},
                )

                conn.execute(
                    text("""
                        DELETE FROM records
                        WHERE id = :id AND nick = :nick
                    """),
                    {"id": project_id, "nick": nick},
                )

            st.session_state.record_mode = "list"
            st.session_state.selected_project_id = None
            st.success("작품을 삭제했어.")
            st.rerun()


# ==================================================
# 작품 목록
# ==================================================

else:
    projects = get_my_records()

    if not projects:
        st.markdown(
            """
            <div class="knit-card">
                <h3>첫 번째 작품을 기록해 봐 🧶</h3>
                <p>작품을 등록하면 도안, 실, 바늘, 게이지 정보를
                작품별로 정리할 수 있어.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.caption(f"등록한 작품 {len(projects)}개")

        for project in projects:
            with st.container(border=True):
                left, right = st.columns([4, 1])

                with left:
                    st.markdown(f"### 🧶 {esc(project['project'])}")
                    st.caption(f"시작일 · {project['record_date']}")

                    if project["content"]:
                        st.write(project["content"][:150])

                    props = q(
                        """
                        SELECT name, value
                        FROM record_properties
                        WHERE record_id = :id
                          AND nick = :nick
                        ORDER BY position, id
                        LIMIT 4
                        """,
                        {
                            "id": project["id"],
                            "nick": nick,
                        },
                    )

                    if props:
                        summary = "　·　".join(
                            f"{item['name']}: {item['value']}"
                            for item in props
                            if item["value"]
                        )

                        if summary:
                            st.caption(summary)

                with right:
                    if st.button(
                        "기록 열기",
                        key=f"open_project_{project['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_project_id = project["id"]
                        st.session_state.record_mode = "detail"
                        st.rerun()
