
import streamlit as st
from datetime import date
from sqlalchemy import text, inspect

from common import setup, header, engine, now, award_points

setup()

nick = st.session_state.nick

# --------------------------------------------------
# 1. 기존 데이터베이스에 없는 열만 추가
# --------------------------------------------------

EXTRA_COLUMNS = {
    "kind": "TEXT DEFAULT ''",
    "status": "TEXT DEFAULT '진행 중'",
    "started_on": "DATE",
    "completed_on": "DATE",
    "pattern_source": "TEXT DEFAULT ''",
    "yarn_type": "TEXT DEFAULT ''",
    "yarn_color": "TEXT DEFAULT ''",
    "yarn_info": "TEXT DEFAULT ''",
    "needle_type": "TEXT DEFAULT ''",
    "needle_size": "TEXT DEFAULT ''",
    "original_gauge": "TEXT DEFAULT ''",
    "gauge_before": "TEXT DEFAULT ''",
    "gauge_after": "TEXT DEFAULT ''",
    "finished_size": "TEXT DEFAULT ''",
    "weight_g": "TEXT DEFAULT ''",
    "notes": "TEXT DEFAULT ''",
    "updated_at": "DATETIME",
}

def migrate_records_table():
    """기존 records 테이블을 유지하면서 누락된 열만 추가한다."""
    inspector = inspect(engine)

    if "records" not in inspector.get_table_names():
        raise RuntimeError(
            "records 테이블이 없습니다. common.py의 테이블 설정을 확인해 주세요."
        )

    existing = {
        column["name"]
        for column in inspector.get_columns("records")
    }

    with engine.begin() as conn:
        for column_name, column_type in EXTRA_COLUMNS.items():
            if column_name not in existing:
                conn.execute(
                    text(
                        f'ALTER TABLE records '
                        f'ADD COLUMN "{column_name}" {column_type}'
                    )
                )

migrate_records_table()


# --------------------------------------------------
# 2. 데이터베이스 도우미 함수
# --------------------------------------------------

def read_records():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *
                FROM records
                WHERE nick = :nick
                ORDER BY
                    CASE WHEN started_on IS NULL THEN 1 ELSE 0 END,
                    started_on DESC,
                    id DESC
            """),
            {"nick": nick},
        )
        return [dict(row) for row in result.mappings().all()]


def read_record(record_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *
                FROM records
                WHERE id = :id AND nick = :nick
            """),
            {"id": record_id, "nick": nick},
        )
        row = result.mappings().first()
        return dict(row) if row else None


def save_record(values, record_id=None):
    """새 기록 저장 또는 기존 기록 수정."""
    values["updated_at"] = now()

    with engine.begin() as conn:
        if record_id is None:
            conn.execute(
                text("""
                    INSERT INTO records (
                        nick, record_date, project, content, created_at,
                        kind, status, started_on, completed_on,
                        pattern_source, yarn_type, yarn_color, yarn_info,
                        needle_type, needle_size, original_gauge,
                        gauge_before, gauge_after, finished_size,
                        weight_g, notes, updated_at
                    ) VALUES (
                        :nick, :record_date, :project, :content, :created_at,
                        :kind, :status, :started_on, :completed_on,
                        :pattern_source, :yarn_type, :yarn_color, :yarn_info,
                        :needle_type, :needle_size, :original_gauge,
                        :gauge_before, :gauge_after, :finished_size,
                        :weight_g, :notes, :updated_at
                    )
                """),
                {
                    **values,
                    "nick": nick,
                    "record_date": date.today(),
                    "created_at": now(),
                },
            )
        else:
            conn.execute(
                text("""
                    UPDATE records SET
                        project = :project,
                        content = :content,
                        kind = :kind,
                        status = :status,
                        started_on = :started_on,
                        completed_on = :completed_on,
                        pattern_source = :pattern_source,
                        yarn_type = :yarn_type,
                        yarn_color = :yarn_color,
                        yarn_info = :yarn_info,
                        needle_type = :needle_type,
                        needle_size = :needle_size,
                        original_gauge = :original_gauge,
                        gauge_before = :gauge_before,
                        gauge_after = :gauge_after,
                        finished_size = :finished_size,
                        weight_g = :weight_g,
                        notes = :notes,
                        updated_at = :updated_at
                    WHERE id = :id AND nick = :nick
                """),
                {**values, "id": record_id, "nick": nick},
            )


# --------------------------------------------------
# 3. 화면
# --------------------------------------------------

st.title("🧶 뜨개 기록장")
st.caption("작품에 사용한 실과 바늘, 진행 상황을 기록해 보세요.")

records_list = read_records()

tab_add, tab_list = st.tabs(["＋ 새 작품 기록", "📚 내 작품 목록"])


# --------------------------------------------------
# 4. 새 작품 기록
# --------------------------------------------------

def record_form(prefix, old=None):
    old = old or {}

    def old_value(key):
        value = old.get(key)
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()[:10]
        return str(value)

    def old_date(key):
        value = old_value(key)
        try:
            return date.fromisoformat(value) if value else None
        except ValueError:
            return None

    with st.form(prefix):
        st.subheader("작품 정보")

        project = st.text_input(
            "작품명 *",
            value=old_value("project"),
            placeholder="예: 복슬복슬 고양이 키링",
        )

        kinds = [
            "인형", "키링", "가방", "의류", "모자",
            "목도리", "소품", "생활용품", "기타",
        ]
        kind_default = old_value("kind")
        kind_options = kinds + (
            [kind_default] if kind_default and kind_default not in kinds else []
        )

        kind = st.selectbox(
            "작품 종류",
            kind_options,
            index=kind_options.index(kind_default)
            if kind_default in kind_options else 0,
        )

        statuses = ["시작 전", "진행 중", "잠시 중단", "완성"]
        status_default = old_value("status") or "진행 중"
        status_options = statuses + (
            [status_default]
            if status_default not in statuses else []
        )

        status = st.selectbox(
            "진행 상태",
            status_options,
            index=status_options.index(status_default),
        )

        col1, col2 = st.columns(2)

        with col1:
            started_on = st.date_input(
                "시작일",
                value=old_date("started_on"),
                key=f"{prefix}_start",
                format="YYYY-MM-DD",
            )

        with col2:
            completed_on = st.date_input(
                "완성일",
                value=old_date("completed_on"),
                key=f"{prefix}_complete",
                format="YYYY-MM-DD",
            )

        st.divider()
        st.subheader("도안 및 실 정보")

        pattern_source = st.text_input(
            "도안 출처",
            value=old_value("pattern_source"),
            placeholder="예: 직접 제작, 책 제목, 웹사이트",
        )

        col1, col2 = st.columns(2)

        with col1:
            yarn_type = st.text_input(
                "실 종류",
                value=old_value("yarn_type"),
                placeholder="예: 면사, 울, 아크릴",
            )

        with col2:
            yarn_color = st.text_input(
                "실 색상",
                value=old_value("yarn_color"),
                placeholder="예: 크림 피치",
            )

        yarn_info = st.text_input(
            "실 정보",
            value=old_value("yarn_info"),
            placeholder="예: 실 이름, 굵기, 사용량",
        )

        st.divider()
        st.subheader("바늘 정보")

        col1, col2 = st.columns(2)

        with col1:
            needle_type = st.selectbox(
                "바늘 종류",
                ["코바늘", "대바늘", "장갑바늘", "기타"],
                index=(
                    ["코바늘", "대바늘", "장갑바늘", "기타"].index(
                        old_value("needle_type")
                    )
                    if old_value("needle_type")
                    in ["코바늘", "대바늘", "장갑바늘", "기타"]
                    else 0
                ),
            )

        with col2:
            needle_size = st.text_input(
                "바늘 크기",
                value=old_value("needle_size"),
                placeholder="예: 3.5mm",
            )

        st.divider()
        st.subheader("게이지 및 완성 정보")

        original_gauge = st.text_input(
            "원래 게이지",
            value=old_value("original_gauge"),
            placeholder="예: 10cm × 10cm에 20코 × 25단",
        )

        col1, col2 = st.columns(2)

        with col1:
            gauge_before = st.text_input(
                "작업 전 게이지",
                value=old_value("gauge_before"),
                placeholder="예: 20코 × 25단",
            )

        with col2:
            gauge_after = st.text_input(
                "작업 후 게이지",
                value=old_value("gauge_after"),
                placeholder="예: 22코 × 27단",
            )

        col1, col2 = st.columns(2)

        with col1:
            finished_size = st.text_input(
                "완성 크기",
                value=old_value("finished_size"),
                placeholder="예: 가로 12cm × 세로 15cm",
            )

        with col2:
            weight_g = st.text_input(
                "무게",
                value=old_value("weight_g"),
                placeholder="예: 45g",
            )

        st.divider()
        st.subheader("메모")

        notes = st.text_area(
            "작업 메모",
            value=old_value("notes") or old_value("content"),
            placeholder="사용한 기법, 어려웠던 점, 다음에 바꾸고 싶은 점 등을 적어 보세요.",
        )

        submitted = st.form_submit_button(
            "기록 저장",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not project.strip():
            st.error("작품명을 입력해 주세요.")
            return None

        if (
            started_on
            and completed_on
            and completed_on < started_on
        ):
            st.error("완성일은 시작일보다 빠를 수 없어요.")
            return None

        return {
            "project": project.strip(),
            "content": notes.strip(),
            "kind": kind,
            "status": status,
            "started_on": started_on,
            "completed_on": completed_on,
            "pattern_source": pattern_source.strip(),
            "yarn_type": yarn_type.strip(),
            "yarn_color": yarn_color.strip(),
            "yarn_info": yarn_info.strip(),
            "needle_type": needle_type,
            "needle_size": needle_size.strip(),
            "original_gauge": original_gauge.strip(),
            "gauge_before": gauge_before.strip(),
            "gauge_after": gauge_after.strip(),
            "finished_size": finished_size.strip(),
            "weight_g": weight_g.strip(),
            "notes": notes.strip(),
        }

    return None


with tab_add:
    new_values = record_form("new_record_form")

    if new_values is not None:
        try:
            save_record(new_values)

            # 새 기록 작성 보상: 하루에 한 번만 지급
            today_key = now().date().isoformat()
            award_points(
                nick,
                f"record-day:{today_key}",
                5,
                "뜨개 기록장 작성",
            )

            st.success("작품 기록을 저장했어요!")
            st.rerun()

        except Exception as error:
            st.error("기록 저장에 실패했어요. common.py의 DB 설정을 확인해 주세요.")
            st.exception(error)


# --------------------------------------------------
# 5. 기존 작품 조회 · 수정 · 삭제
# --------------------------------------------------

with tab_list:
    records_list = read_records()

    if not records_list:
        st.info("아직 등록한 작품이 없어요. 새 작품 기록을 추가해 보세요.")
    else:
        st.caption(f"총 {len(records_list)}개의 작품")

        labels = {
            row["id"]: (
                f'{row.get("project") or "이름 없는 작품"}'
                f' · {row.get("status") or "상태 미설정"}'
            )
            for row in records_list
        }

        selected_id = st.selectbox(
            "확인할 작품 선택",
            options=list(labels.keys()),
            format_func=lambda record_id: labels[record_id],
        )

        selected = read_record(selected_id)

        if selected:
            st.subheader(selected.get("project") or "이름 없는 작품")
            st.write(f"**종류:** {selected.get('kind') or '미입력'}")
            st.write(f"**진행 상태:** {selected.get('status') or '미입력'}")

            def display_value(label, key):
                value = selected.get(key)
                st.write(f"**{label}:** {value if value not in (None, '') else '미입력'}")

            st.divider()
            st.markdown("#### 도안 및 재료")
            display_value("도안 출처", "pattern_source")
            display_value("실 종류", "yarn_type")
            display_value("실 색상", "yarn_color")
            display_value("실 정보", "yarn_info")
            display_value("바늘 종류", "needle_type")
            display_value("바늘 크기", "needle_size")

            st.divider()
            st.markdown("#### 작업 및 완성 정보")
            display_value("시작일", "started_on")
            display_value("완성일", "completed_on")
            display_value("원래 게이지", "original_gauge")
            display_value("작업 전 게이지", "gauge_before")
            display_value("작업 후 게이지", "gauge_after")
            display_value("완성 크기", "finished_size")
            display_value("무게", "weight_g")
            display_value("메모", "notes")

            display_value("최초 기록일", "created_at")
            display_value("마지막 수정일", "updated_at")

            st.divider()

            with st.expander("✏️ 작품 정보 수정"):
                edited_values = record_form(
                    f"edit_record_{selected_id}",
                    old=selected,
                )

                if edited_values is not None:
                    try:
                        save_record(edited_values, record_id=selected_id)
                        st.success("작품 기록을 수정했어요.")
                        st.rerun()
                    except Exception as error:
                        st.error("수정에 실패했어요.")
                        st.exception(error)

            with st.expander("🗑️ 작품 기록 삭제"):
                st.warning("삭제한 기록은 복구하기 어려우니 신중하게 선택해 주세요.")

                confirm_delete = st.checkbox(
                    "이 작품 기록을 삭제하겠습니다.",
                    key=f"confirm_delete_{selected_id}",
                )

                if st.button(
                    "작품 기록 삭제",
                    key=f"delete_record_{selected_id}",
                    disabled=not confirm_delete,
                    use_container_width=True,
                ):
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    DELETE FROM records
                                    WHERE id = :id AND nick = :nick
                                """),
                                {"id": selected_id, "nick": nick},
                            )

                        st.success("작품 기록을 삭제했어요.")
                        st.rerun()
                    except Exception as error:
                        st.error("삭제에 실패했어요.")
                        st.exception(error)

