
import streamlit as st
from datetime import date

from common import (
    setup, header, q, engine, records, now,
    check_text, award_points, esc
)

setup()
nick = st.session_state.nick

st.markdown(
    """
    <style>
    .record-title {
        font-size: 2.15rem;
        font-weight: 750;
        letter-spacing: -0.06em;
        margin: 0.2rem 0 1.2rem;
    }
    .property-label {
        color: #77716B;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .property-value {
        color: #26221E;
        font-size: 0.98rem;
        padding: 5px 10px;
        border-radius: 6px;
        background: rgba(130, 120, 105, 0.08);
        display: inline-block;
        overflow-wrap: anywhere;
    }
    .property-empty {
        color: #96908A;
        font-size: 0.95rem;
    }
    .record-section {
        color: #B5502E;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------
# 데이터 조회
# -----------------------------------

def get_projects():
    return q(
        """
        SELECT *
        FROM records
        WHERE nick = :nick
        ORDER BY id DESC
        """,
        {"nick": nick},
    )


def get_project(project_id):
    result = q(
        """
        SELECT *
        FROM records
        WHERE id = :id AND nick = :nick
        LIMIT 1
        """,
        {"id": project_id, "nick": nick},
    )
    return result[0] if result else None


def value_or_empty(value):
    if value is None or str(value).strip() == "":
        return "비어 있음"
    return str(value)


def show_property(label, value):
    shown = value_or_empty(value)
    is_empty = shown == "비어 있음"

    value_class = "property-empty" if is_empty else "property-value"

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns: 145px minmax(0,1fr);
                    gap:12px; align-items:start; margin:8px 0;">
            <div class="property-label">{esc(label)}</div>
            <div class="{value_class}">{esc(shown)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_status(status):
    status_colors = {
        "준비 중": "#E9E2D7",
        "진행 중": "#DCE8FF",
        "마무리 중": "#F8E5C7",
        "완성": "#D9EBDD",
        "보류": "#E8E4E1",
    }
    color = status_colors.get(status, "#E8E4E1")

    st.markdown(
        f"""
        <span style="background:{color}; padding:4px 10px;
                     border-radius:6px; font-size:0.9rem;">
            ● {esc(status or "준비 중")}
        </span>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------
# 페이지 제목과 작품 목록
# -----------------------------------

st.markdown(
    '<div class="record-title">🧶 나의 뜨개 기록장</div>',
    unsafe_allow_html=True,
)

st.caption("작품마다 도안, 실, 바늘, 게이지와 작업 과정을 정리해.")

projects = get_projects()

if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None

if (
    st.session_state.selected_project_id is not None
    and not any(
        p["id"] == st.session_state.selected_project_id
        for p in projects
    )
):
    st.session_state.selected_project_id = None

with st.sidebar:
    st.markdown("### 🧵 작품 목록")

    if st.button("＋ 새 작품", use_container_width=True):
        st.session_state.selected_project_id = None
        st.session_state.record_mode = "create"
        st.rerun()

    if not projects:
        st.caption("아직 등록된 작품이 없어.")
    else:
        for project in projects:
            project_name = project.get("project") or "이름 없는 작품"
            status = project.get("status") or "준비 중"

            if st.button(
                f"{project_name}\n{status}",
                key=f"select_{project['id']}",
                use_container_width=True,
            ):
                st.session_state.selected_project_id = project["id"]
                st.session_state.record_mode = "view"
                st.rerun()


# -----------------------------------
# 새 작품 등록
# -----------------------------------

mode = st.session_state.get("record_mode", "view")
selected_id = st.session_state.selected_project_id

if mode == "create":
    st.subheader("새 작품 등록")
    st.caption("작품의 기본 정보를 입력해 줘.")

    with st.form("create_record_form"):
        title = st.text_input(
            "작품명 *",
            placeholder="예: 밀키웨이 가디건",
            max_chars=80,
        )

        col1, col2 = st.columns(2)

        with col1:
            kind = st.selectbox(
                "유형",
                ["대바늘", "코바늘", "아프간뜨기", "기타"],
            )

            status = st.selectbox(
                "상태",
                ["준비 중", "진행 중", "마무리 중", "완성", "보류"],
                index=1,
            )

            completed_on = st.date_input(
                "완성일",
                value=None,
            )

            pattern_source = st.text_input(
                "도안",
                placeholder="예: 밀키웨이 가디건 by. 코실니트",
                max_chars=200,
            )

        with col2:
            needle_type = st.text_input(
                "바늘 종류",
                placeholder="예: 니트프로 심포니",
                max_chars=100,
            )

            yarn_info = st.text_input(
                "실 정보",
                placeholder="예: 바늘이야기 세틴 알파카 모헤어",
                max_chars=200,
            )

            needle_size = st.text_input(
                "바늘",
                placeholder="예: 4mm",
                max_chars=50,
            )

        st.divider()
        st.markdown("#### 게이지와 완성 정보")

        original_gauge = st.text_input(
            "원작게이지",
            placeholder="예: 10cm에 22코 30단",
            max_chars=100,
        )

        gauge_before = st.text_input(
            "세탁 전 게이지",
            placeholder="예: 24코 31단",
            max_chars=100,
        )

        gauge_after = st.text_input(
            "세탁 후 게이지",
            placeholder="예: 22코 32단",
            max_chars=100,
        )

        finished_size = st.text_input(
            "사이즈",
            placeholder="예: 가슴둘레 100cm, 총장 55cm",
            max_chars=100,
        )

        weight_g = st.number_input(
            "무게(g)",
            min_value=0,
            max_value=100000,
            value=0,
            step=1,
        )

        notes = st.text_area(
            "작업 메모",
            placeholder="작업 중 수정한 부분이나 다음에 할 일을 적어 줘.",
            max_chars=3000,
        )

        save_new = st.form_submit_button(
            "작품 저장",
            type="primary",
            use_container_width=True,
        )

    if save_new:
        valid, clean_title = check_text(title, 80)

        if not valid:
            st.warning("작품명을 입력해 줘.")
        else:
            try:
                with engine.begin() as conn:
                    result = conn.execute(
                        records.insert().values(
                            nick=nick,
                            record_date=date.today().isoformat(),
                            project=clean_title,
                            content=notes.strip(),
                            created_at=now(),
                            kind=kind,
                            status=status,
                            started_on=date.today().isoformat(),
                            completed_on=(
                                completed_on.isoformat()
                                if completed_on else None
                            ),
                            pattern_source=pattern_source.strip() or None,
                            yarn_type=None,
                            yarn_color=None,
                            yarn_info=yarn_info.strip() or None,
                            needle_type=needle_type.strip() or None,
                            needle_size=needle_size.strip() or None,
                            original_gauge=original_gauge.strip() or None,
                            gauge_before=gauge_before.strip() or None,
                            gauge_after=gauge_after.strip() or None,
                            finished_size=finished_size.strip() or None,
                            weight_g=int(weight_g) if weight_g else None,
                            notes=notes.strip() or None,
                            updated_at=now(),
                        )
                    )

                    new_id = result.inserted_primary_key[0]

                # 작품 등록 자체는 여러 번 가능하지만
                # 같은 날 기록장 보상은 한 번만 지급
                award_points(
                    nick,
                    f"record-day:{date.today().isoformat()}",
                    5,
                    "뜨개 기록장 작성",
                )

                st.session_state.selected_project_id = new_id
                st.session_state.record_mode = "view"
                st.success("작품을 기록장에 저장했어.")
                st.rerun()

            except Exception as error:
                st.error("저장에 실패했어. 데이터베이스 열 설정을 확인해 줷.")
                st.caption(type(error).__name__)


# -----------------------------------
# 작품 상세 보기
# -----------------------------------

elif selected_id is not None:
    project = get_project(selected_id)

    if project is None:
        st.warning("작품을 찾을 수 없어.")
    else:
        st.markdown(
            f'<div class="record-title">🧶 {esc(project.get("project"))}</div>',
            unsafe_allow_html=True,
        )

        show_property("유형", project.get("kind"))
        show_property("상태", project.get("status"))
        show_property("완성일", project.get("completed_on"))
        show_property("도안", project.get("pattern_source"))
        show_property("바늘 종류", project.get("needle_type"))
        show_property("실 정보", project.get("yarn_info"))
        show_property("바늘", project.get("needle_size"))
        show_property("원작게이지", project.get("original_gauge"))
        show_property("세탁 전 게이지", project.get("gauge_before"))
        show_property("세탁 후 게이지", project.get("gauge_after"))
        show_property("사이즈", project.get("finished_size"))

        weight = project.get("weight_g")
        show_property(
            "무게",
            f"{weight}g" if weight is not None else None,
        )

        st.divider()
        st.subheader("작업 메모")
        st.write(project.get("notes") or "아직 작성된 메모가 없어.")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("✏️ 작품 수정", use_container_width=True):
                st.session_state.record_mode = "edit"
                st.rerun()

        with c2:
            if st.button("🗑️ 작품 삭제", use_container_width=True):
                st.session_state.record_mode = "delete"
                st.rerun()


# -----------------------------------
# 작품 수정
# -----------------------------------

if mode == "edit" and selected_id is not None:
    project = get_project(selected_id)

    if project:
        st.divider()
        st.subheader("작품 정보 수정")

        with st.form(f"edit_record_{selected_id}"):
            edit_title = st.text_input(
                "작품명",
                value=project.get("project") or "",
                max_chars=80,
            )

            edit_kind = st.selectbox(
                "유형",
                ["대바늘", "코바늘", "아프간뜨기", "기타"],
                index=(
                    ["대바늘", "코바늘", "아프간뜨기", "기타"].index(
                        project["kind"]
                    )
                    if project.get("kind") in
                    ["대바늘", "코바늘", "아프간뜨기", "기타"]
                    else 0
                ),
            )

            status_options = [
                "준비 중", "진행 중", "마무리 중", "완성", "보류"
            ]
            old_status = project.get("status") or "준비 중"

            edit_status = st.selectbox(
                "상태",
                status_options,
                index=(
                    status_options.index(old_status)
                    if old_status in status_options else 0
                ),
            )

            edit_completed = st.text_input(
                "완성일 (YYYY-MM-DD)",
                value=project.get("completed_on") or "",
                placeholder="완성 전이면 비워 둬.",
            )

            edit_pattern = st.text_input(
                "도안",
                value=project.get("pattern_source") or "",
            )
            edit_needle_type = st.text_input(
                "바늘 종류",
                value=project.get("needle_type") or "",
            )
            edit_yarn = st.text_input(
                "실 정보",
                value=project.get("yarn_info") or "",
            )
            edit_needle_size = st.text_input(
                "바늘",
                value=project.get("needle_size") or "",
            )
            edit_original_gauge = st.text_input(
                "원작게이지",
                value=project.get("original_gauge") or "",
            )
            edit_before = st.text_input(
                "세탁 전 게이지",
                value=project.get("gauge_before") or "",
            )
            edit_after = st.text_input(
                "세탁 후 게이지",
                value=project.get("gauge_after") or "",
            )
            edit_size = st.text_input(
                "사이즈",
                value=project.get("finished_size") or "",
            )

            old_weight = project.get("weight_g")
            edit_weight = st.number_input(
                "무게(g)",
                min_value=0,
                max_value=100000,
                value=max(0, int(old_weight or 0)),
            )

            edit_notes = st.text_area(
                "작업 메모",
                value=project.get("notes") or "",
                max_chars=3000,
            )

            save_edit = st.form_submit_button(
                "수정 내용 저장",
                type="primary",
            )

        if save_edit:
            valid, clean_title = check_text(edit_title, 80)

            if not valid:
                st.warning("작품명을 확인해 줘.")
            else:
                completed_value = None

                if edit_completed.strip():
                    try:
                        completed_value = date.fromisoformat(
                            edit_completed.strip()
                        ).isoformat()
                    except ValueError:
                        st.error("완성일은 YYYY-MM-DD 형식으로 입력해 줘.")

                if not edit_completed.strip() or completed_value:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                records.update()
                                .where(
                                    records.c.id == selected_id,
                                    records.c.nick == nick,
                                )
                                .values(
                                    project=clean_title,
                                    kind=edit_kind,
                                    status=edit_status,
                                    completed_on=completed_value,
                                    pattern_source=edit_pattern.strip() or None,
                                    needle_type=edit_needle_type.strip() or None,
                                    yarn_info=edit_yarn.strip() or None,
                                    needle_size=edit_needle_size.strip() or None,
                                    original_gauge=edit_original_gauge.strip() or None,
                                    gauge_before=edit_before.strip() or None,
                                    gauge_after=edit_after.strip() or None,
                                    finished_size=edit_size.strip() or None,
                                    weight_g=int(edit_weight) if edit_weight else None,
                                    notes=edit_notes.strip() or None,
                                    content=edit_notes.strip(),
                                    updated_at=now(),
                                )
                            )

                        st.session_state.record_mode = "view"
                        st.success("작품 정보를 수정했어.")
                        st.rerun()

                    except Exception as error:
                        st.error("수정에 실패했어.")
                        st.caption(type(error).__name__)


# -----------------------------------
# 작품 삭제
# -----------------------------------

if mode == "delete" and selected_id is not None:
    project = get_project(selected_id)

    if project:
        st.warning(
            f"'{project.get('project')}' 기록을 삭제할까? "
            "삭제한 기록은 복구할 수 없어."
        )

        yes, no = st.columns(2)

        with yes:
            if st.button("삭제 확정", type="primary"):
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            records.delete().where(
                                records.c.id == selected_id,
                                records.c.nick == nick,
                            )
                        )

                    st.session_state.selected_project_id = None
                    st.session_state.record_mode = "view"
                    st.success("작품 기록을 삭제했어.")
                    st.rerun()

                except Exception as error:
                    st.error("삭제에 실패했어.")
                    st.caption(type(error).__name__)

        with no:
            if st.button("취소"):
                st.session_state.record_mode = "view"
                st.rerun()


# -----------------------------------
# 빈 상태 안내
# -----------------------------------

if not projects and mode != "create":
    st.markdown(
        """
        <div class="knit-card">
          <h3>첫 번째 작품을 기록해 봐 🧶</h3>
          <p>작품을 등록하면 이곳에 작품별 기록이 쌓여.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.caption("knit. · 한 작품의 시작부터 완성까지.")


st.caption("작품마다 도안, 실, 바늘, 게이지와 작업 과정을 정리해.")

# 기록장 시작 버튼을 페이지 상단에 표시
top_left, top_right = st.columns([3, 1])

with top_left:
    st.markdown("#### 나만의 뜨개 작품을 모아 봐")
    st.caption("새 작품을 등록하고 실, 바늘, 게이지 정보를 기록할 수 있어.")

with top_right:
    if st.button(
        "＋ 새 작품 기록하기",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.selected_project_id = None
        st.session_state.record_mode = "create"
        st.rerun()

projects = get_projects()
