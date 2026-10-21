# pages/뜨개 기록.py

import streamlit as st
import pandas as pd
from datetime import date

from common import (
    setup,
    header,
    q,
    ex,
    init_record_options_once,
    get_record_options,
    add_record_option,
    rename_record_option,
    delete_record_option,
)

setup()
init_record_options_once()

header("나의 뜨개 기록장", "작품과 뜨개 정보를 차곡차곡 기록해 보세요.")


# --------------------------------------------------
# 기본 옵션
# --------------------------------------------------

DEFAULT_OPTIONS = {
    "종류": ["의류", "가방", "소품", "인형", "홈데코", "기타"],
    "상태": ["예정", "진행 중", "완성", "보류"],
    "실 종류": ["울", "면", "아크릴", "혼방", "모헤어", "기타"],
    "실 색상": ["크림", "베이지", "핑크", "브라운", "그레이", "기타"],
    "바늘 종류": ["대바늘", "코바늘", "아프간바늘", "기타"],
}

RECORD_FIELDS = [
    "id",
    "nick",
    "record_date",
    "project",
    "content",
    "created_at",
    "kind",
    "status",
    "start_date",
    "finish_date",
    "pattern_source",
    "yarn_type",
    "yarn_color",
    "yarn_info",
    "needle_type",
    "needle_size",
    "gauge_original",
    "gauge_before",
    "gauge_after",
    "finished_size",
    "weight",
    "memo",
]


# --------------------------------------------------
# 사용자 확인
# --------------------------------------------------

# 프로젝트의 로그인 방식에 맞게 수정할 수 있는 부분
nick = (
    st.session_state.get("nick")
    or st.session_state.get("nickname")
    or st.session_state.get("user_nick")
)

if not nick:
    st.warning("먼저 메인 페이지에서 로그인하거나 닉네임을 설정해 주세요.")
    st.stop()


# --------------------------------------------------
# 기존 records 테이블 확장
# --------------------------------------------------

def ensure_record_columns():
    """
    기존 records 테이블에 필요한 컬럼이 없으면 추가한다.
    기존 작품 기록은 삭제하지 않는다.
    """
    existing = q("PRAGMA table_info(records)")

    # SQLite에서는 PRAGMA로 열 목록을 확인할 수 있다.
    # 다른 DB를 사용한다면 이 함수는 해당 DB 방식에 맞춰야 한다.
    existing_names = {
        row["name"] for row in existing
    }

    column_types = {
        "kind": "TEXT",
        "status": "TEXT",
        "start_date": "TEXT",
        "finish_date": "TEXT",
        "pattern_source": "TEXT",
        "yarn_type": "TEXT",
        "yarn_color": "TEXT",
        "yarn_info": "TEXT",
        "needle_type": "TEXT",
        "needle_size": "TEXT",
        "gauge_original": "TEXT",
        "gauge_before": "TEXT",
        "gauge_after": "TEXT",
        "finished_size": "TEXT",
        "weight": "TEXT",
        "memo": "TEXT",
    }

    for column, column_type in column_types.items():
        if column not in existing_names:
            ex(
                f"ALTER TABLE records ADD COLUMN {column} {column_type}"
            )


ensure_record_columns()


# --------------------------------------------------
# 옵션 불러오기
# --------------------------------------------------

def options_for(category):
    return get_record_options(
        nick,
        category,
        DEFAULT_OPTIONS.get(category, []),
    )


# --------------------------------------------------
# 옵션 관리 화면
# --------------------------------------------------

with st.expander("⚙️ 나만의 뜨개 옵션 관리", expanded=False):
    st.caption(
        "옵션을 추가하면 데이터베이스에 저장되어 "
        "다음에 접속해도 유지됩니다."
    )

    category = st.selectbox(
        "관리할 항목",
        list(DEFAULT_OPTIONS.keys()),
        key="manage_category",
    )

    current_options = options_for(category)

    st.write("현재 옵션")
    st.write(" · ".join(current_options) if current_options else "등록된 옵션이 없습니다.")

    with st.form("add_option_form", clear_on_submit=True):
        new_option = st.text_input("새 옵션 이름")
        add_clicked = st.form_submit_button("옵션 추가")

    if add_clicked:
        if not new_option.strip():
            st.warning("옵션 이름을 입력해 주세요.")
        elif new_option.strip() in current_options:
            st.info("이미 존재하는 옵션입니다.")
        elif add_record_option(nick, category, new_option.strip()):
            st.success("옵션을 저장했습니다.")
            st.rerun()
        else:
            st.error("옵션 저장에 실패했습니다. 데이터베이스 연결을 확인해 주세요.")

    st.divider()
    st.subheader("옵션 이름 수정")

    saved_options = q(
        """
        SELECT option_value
        FROM record_options
        WHERE nick = ? AND category = ?
        ORDER BY id
        """,
        (nick, category),
    )

    if saved_options:
        old_option = st.selectbox(
            "수정할 사용자 옵션",
            [row["option_value"] for row in saved_options],
            key="rename_old",
        )

        new_name = st.text_input(
            "변경할 이름",
            value=old_option,
            key="rename_new",
        )

        if st.button("옵션 이름 변경"):
            if not new_name.strip():
                st.warning("새 이름을 입력해 주세요.")
            elif new_name.strip() in current_options and new_name.strip() != old_option:
                st.warning("이미 존재하는 옵션 이름입니다.")
            elif rename_record_option(
                nick, category, old_option, new_name.strip()
            ):
                st.success("옵션 이름을 변경했습니다.")
                st.rerun()
            else:
                st.error("이름 변경에 실패했습니다.")

        st.divider()
        st.subheader("사용자 옵션 삭제")

        delete_target = st.selectbox(
            "삭제할 옵션",
            [row["option_value"] for row in saved_options],
            key="delete_target",
        )

        if st.button("선택한 옵션 삭제"):
            delete_record_option(nick, category, delete_target)
            st.success("옵션을 삭제했습니다.")
            st.rerun()

    else:
        st.info("수정하거나 삭제할 사용자 지정 옵션이 없습니다.")


# --------------------------------------------------
# 작품 등록
# --------------------------------------------------

st.divider()
st.subheader("🧶 새 작품 기록")

with st.form("new_record_form", clear_on_submit=True):

    project = st.text_input("작품명 *")

    col1, col2 = st.columns(2)

    with col1:
        kind = st.selectbox(
            "작품 종류",
            options_for("종류"),
        )

        status = st.selectbox(
            "진행 상태",
            options_for("상태"),
        )

        start_date = st.date_input(
            "시작일",
            value=date.today(),
        )

        yarn_type = st.selectbox(
            "실 종류",
            options_for("실 종류"),
        )

        yarn_color = st.selectbox(
            "실 색상",
            options_for("실 색상"),
        )

        yarn_info = st.text_input(
            "실 상세 정보",
            placeholder="예: 브랜드, 제품명, 실 굵기",
        )

    with col2:
        finish_date = st.date_input(
            "완성일",
            value=None,
        )

        pattern_source = st.text_input(
            "도안 출처",
            placeholder="예: 도안 링크, 책 제목, 제작자",
        )

        needle_type = st.selectbox(
            "바늘 종류",
            options_for("바늘 종류"),
        )

        needle_size = st.text_input(
            "바늘 크기",
            placeholder="예: 코바늘 3.5mm",
        )

        gauge_original = st.text_input(
            "원래 게이지",
            placeholder="예: 10cm × 10cm, 20코 × 25단",
        )

    gauge_before = st.text_input(
        "세탁 전 게이지",
        placeholder="예: 10cm × 10cm, 20코 × 25단",
    )

    gauge_after = st.text_input(
        "세탁 후 게이지",
        placeholder="예: 10cm × 10cm, 19코 × 24단",
    )

    finished_size = st.text_input(
        "완성 크기",
        placeholder="예: 가로 20cm × 세로 25cm",
    )

    weight = st.text_input(
        "사용 무게",
        placeholder="예: 120g",
    )

    memo = st.text_area(
        "작업 메모",
        placeholder="사용한 기법, 어려웠던 점, 다음에 바꿀 점 등을 기록하세요.",
    )

    submitted = st.form_submit_button(
        "작품 기록 저장",
        use_container_width=True,
    )

if submitted:
    if not project.strip():
        st.warning("작품명을 입력해 주세요.")
    else:
        try:
            ex(
                """
                INSERT INTO records (
                    nick,
                    record_date,
                    project,
                    content,
                    kind,
                    status,
                    start_date,
                    finish_date,
                    pattern_source,
                    yarn_type,
                    yarn_color,
                    yarn_info,
                    needle_type,
                    needle_size,
                    gauge_original,
                    gauge_before,
                    gauge_after,
                    finished_size,
                    weight,
                    memo
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    nick,
                    str(date.today()),
                    project.strip(),
                    memo.strip(),
                    kind,
                    status,
                    str(start_date) if start_date else None,
                    str(finish_date) if finish_date else None,
                    pattern_source.strip(),
                    yarn_type,
                    yarn_color,
                    yarn_info.strip(),
                    needle_type,
                    needle_size.strip(),
                    gauge_original.strip(),
                    gauge_before.strip(),
                    gauge_after.strip(),
                    finished_size.strip(),
                    weight.strip(),
                    memo.strip(),
                ),
            )

            st.success("작품 기록을 저장했습니다.")
            st.rerun()

        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")


# --------------------------------------------------
# 내 작품 목록
# --------------------------------------------------

st.divider()
st.subheader("📚 내 작품 목록")

records = q(
    """
    SELECT *
    FROM records
    WHERE nick = ?
    ORDER BY id DESC
    """,
    (nick,),
)

if not records:
    st.info("아직 기록한 작품이 없습니다.")
else:
    filter_status = st.selectbox(
        "상태별 보기",
        ["전체"] + options_for("상태"),
    )

    filtered = [
        dict(row) for row in records
        if filter_status == "전체"
        or row["status"] == filter_status
    ]

    st.caption(f"총 {len(filtered)}개의 작품")

    for record in filtered:
        with st.expander(
            f"🧶 {record['project']} · {record.get('status') or '상태 미지정'}"
        ):
            st.write(f"**종류:** {record.get('kind') or '-'}")
            st.write(f"**시작일:** {record.get('start_date') or '-'}")
            st.write(f"**완성일:** {record.get('finish_date') or '-'}")
            st.write(f"**도안 출처:** {record.get('pattern_source') or '-'}")
            st.write(f"**실 종류:** {record.get('yarn_type') or '-'}")
            st.write(f"**실 색상:** {record.get('yarn_color') or '-'}")
            st.write(f"**실 정보:** {record.get('yarn_info') or '-'}")
            st.write(f"**바늘 종류:** {record.get('needle_type') or '-'}")
            st.write(f"**바늘 크기:** {record.get('needle_size') or '-'}")
            st.write(f"**원래 게이지:** {record.get('gauge_original') or '-'}")
            st.write(f"**세탁 전 게이지:** {record.get('gauge_before') or '-'}")
            st.write(f"**세탁 후 게이지:** {record.get('gauge_after') or '-'}")
            st.write(f"**완성 크기:** {record.get('finished_size') or '-'}")
            st.write(f"**무게:** {record.get('weight') or '-'}")
            st.write(f"**메모:** {record.get('memo') or '-'}")

            st.divider()
            st.subheader("기록 수정")

            with st.form(f"edit_record_{record['id']}"):
                edit_project = st.text_input(
                    "작품명",
                    value=record.get("project") or "",
                )

                edit_kind = st.selectbox(
                    "종류",
                    options_for("종류"),
                    index=(
                        options_for("종류").index(record["kind"])
                        if record.get("kind") in options_for("종류")
                        else 0
                    ),
                )

                edit_status = st.selectbox(
                    "상태",
                    options_for("상태"),
                    index=(
                        options_for("상태").index(record["status"])
                        if record.get("status") in options_for("상태")
                        else 0
                    ),
                )

                edit_memo = st.text_area(
                    "메모",
                    value=record.get("memo") or "",
                )

                edit_saved = st.form_submit_button("기록 수정 저장")

            if edit_saved:
                ex(
                    """
                    UPDATE records
                    SET project = ?, kind = ?, status = ?,
                        content = ?, memo = ?
                    WHERE id = ? AND nick = ?
                    """,
                    (
                        edit_project.strip(),
                        edit_kind,
                        edit_status,
                        edit_memo.strip(),
                        edit_memo.strip(),
                        record["id"],
                        nick,
                    ),
                )

                st.success("기록을 수정했습니다.")
                st.rerun()

            if st.button(
                "이 작품 삭제",
                key=f"delete_record_{record['id']}",
            ):
                ex(
                    "DELETE FROM records WHERE id = ? AND nick = ?",
                    (record["id"], nick),
                )
                st.success("작품을 삭제했습니다.")
                st.rerun()
