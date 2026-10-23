
# pages/뜨개 기록.py

import streamlit as st
from datetime import date, datetime

from common import (
    setup,
    header,
    q,
    ex,
    now,
    award_points,
    init_record_options_once,
    get_record_options,
    add_record_option,
    rename_record_option,
    delete_record_option,
)

# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

setup()
init_record_options_once()
header()

st.markdown(
    """
    <style>
    .record-intro {
        padding: 24px;
        background: linear-gradient(135deg, #fff8f0, #fff0f2);
        border: 1px solid #f2e3dc;
        border-radius: 18px;
        margin-bottom: 20px;
    }
    .record-intro h2 {
        margin: 0 0 8px 0;
        color: #704d40;
        font-size: 25px;
    }
    .record-intro p {
        margin: 0;
        color: #8b7469;
        font-size: 14px;
    }
    .section-label {
        font-size: 17px;
        font-weight: 700;
        color: #725447;
        padding: 8px 0;
        border-bottom: 1px solid #eee2dc;
        margin: 12px 0;
    }
    .property-label {
        color: #88766e;
        font-size: 13px;
    }
    div[data-testid="stForm"] {
        border: 1px solid #eee4df;
        border-radius: 14px;
        padding: 20px;
    }
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 10px;
    }
    </style>

    <div class="record-intro">
        <h2>🧶 나의 뜨개 기록장</h2>
        <p>한 코 한 코 쌓아 가는 나만의 작품 기록.</p>
        <p>작품 정보를 한 번에 작성하고 한 번에 저장해 보세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

nick = (
    st.session_state.get("nick")
    or st.session_state.get("nickname")
    or st.session_state.get("user_nick")
)

if not nick:
    st.warning("먼저 메인 화면에서 닉네임을 설정해 주세요.")
    st.stop()


# --------------------------------------------------
# 2. 기본 옵션
# --------------------------------------------------

DEFAULT_OPTIONS = {
    "종류": ["의류", "가방", "소품", "인형", "홈데코", "기타"],
    "상태": ["예정", "진행 중", "완성", "보류"],
    "실 종류": ["울", "면", "아크릴", "혼방", "모헤어", "기타"],
    "실 색상": ["크림", "베이지", "핑크", "브라운", "그레이", "기타"],
    "바늘 종류": ["대바늘", "코바늘", "아프간바늘", "기타"],
}


def options_for(category, current_value=None):
    """기본 옵션과 사용자가 추가한 옵션을 함께 제공한다."""
    saved = get_record_options(
        nick,
        category,
        DEFAULT_OPTIONS.get(category, []),
    )

    result = list(saved or DEFAULT_OPTIONS.get(category, []))

    if current_value and current_value not in result:
        result.append(current_value)

    if not result:
        result = ["기타"]

    return result


# --------------------------------------------------
# 3. 기존 데이터베이스 열 확인 및 보완
# --------------------------------------------------

def ensure_record_columns():
    """
    기존 records 테이블에 빠진 열만 추가한다.
    기존 작품 데이터는 삭제하지 않는다.
    SQLite 데이터베이스를 기준으로 한다.
    """
    table_info = q("PRAGMA table_info(records)")
    existing = {row["name"] for row in table_info}

    if not existing:
        raise RuntimeError(
            "records 테이블을 찾을 수 없습니다. common.py의 테이블 설정을 확인해 주세요."
        )

    columns = {
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
        "updated_at": "TEXT",
    }

    for column, column_type in columns.items():
        if column not in existing:
            ex(
                f'ALTER TABLE records ADD COLUMN "{column}" {column_type}'
            )


ensure_record_columns()


# --------------------------------------------------
# 4. 날짜 및 기록 관련 함수
# --------------------------------------------------

def date_value(value):
    """데이터베이스 날짜를 date 객체로 변환한다."""
    if not value:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def text_value(value):
    return "" if value is None else str(value)


def get_records():
    return q(
        """
        SELECT *
        FROM records
        WHERE nick = :nick
        ORDER BY id DESC
        """,
        {"nick": nick},
    )


def get_record(record_id):
    rows = q(
        """
        SELECT *
        FROM records
        WHERE id = :id AND nick = :nick
        """,
        {"id": record_id, "nick": nick},
    )
    return dict(rows[0]) if rows else None


def save_record(values, record_id=None):
    """모든 입력 항목을 한 번의 DB 작업으로 저장하거나 수정한다."""
    current_time = str(now())

    if record_id is None:
        ex(
            """
            INSERT INTO records (
                nick, record_date, project, content, created_at,
                kind, status, start_date, finish_date,
                pattern_source, yarn_type, yarn_color, yarn_info,
                needle_type, needle_size, gauge_original,
                gauge_before, gauge_after, finished_size,
                weight, memo, updated_at
            )
            VALUES (
                :nick, :record_date, :project, :content, :created_at,
                :kind, :status, :start_date, :finish_date,
                :pattern_source, :yarn_type, :yarn_color, :yarn_info,
                :needle_type, :needle_size, :gauge_original,
                :gauge_before, :gauge_after, :finished_size,
                :weight, :memo, :updated_at
            )
            """,
            {
                **values,
                "nick": nick,
                "record_date": str(date.today()),
                "created_at": current_time,
                "updated_at": current_time,
            },
        )
    else:
        ex(
            """
            UPDATE records
            SET project = :project,
                content = :content,
                kind = :kind,
                status = :status,
                start_date = :start_date,
                finish_date = :finish_date,
                pattern_source = :pattern_source,
                yarn_type = :yarn_type,
                yarn_color = :yarn_color,
                yarn_info = :yarn_info,
                needle_type = :needle_type,
                needle_size = :needle_size,
                gauge_original = :gauge_original,
                gauge_before = :gauge_before,
                gauge_after = :gauge_after,
                finished_size = :finished_size,
                weight = :weight,
                memo = :memo,
                updated_at = :updated_at
            WHERE id = :id AND nick = :nick
            """,
            {
                **values,
                "id": record_id,
                "nick": nick,
                "updated_at": current_time,
            },
        )


# --------------------------------------------------
# 5. 한 번에 입력하는 작품 폼
# --------------------------------------------------

def render_record_form(form_key, old=None, submit_label="작품 기록 저장"):
    """
    모든 입력 항목을 하나의 form에 배치한다.
    입력 항목별 저장 버튼은 사용하지 않는다.
    """
    old = dict(old or {})

    def val(key):
        return text_value(old.get(key))

    def old_date(key):
        return date_value(old.get(key))

    st.markdown("#### 📌 작품 기본 정보")

    with st.form(form_key, clear_on_submit=(old.get("id") is None)):
        project = st.text_input(
            "작품명 *",
            value=val("project"),
            placeholder="예: 복슬복슬 고양이 키링",
        )

        col1, col2 = st.columns(2)

        with col1:
            kind_options = options_for("종류", val("kind"))
            kind = st.selectbox(
                "작품 종류",
                kind_options,
                index=(
                    kind_options.index(val("kind"))
                    if val("kind") in kind_options else 0
                ),
            )

        with col2:
            status_options = options_for("상태", val("status"))
            status = st.selectbox(
                "진행 상태",
                status_options,
                index=(
                    status_options.index(val("status"))
                    if val("status") in status_options else 0
                ),
            )

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "시작일",
                value=old_date("start_date") or date.today(),
                key=f"{form_key}_start_date",
                format="YYYY-MM-DD",
            )

        with col2:
            finish_date = st.date_input(
                "완성일 (선택)",
                value=old_date("finish_date"),
                key=f"{form_key}_finish_date",
                format="YYYY-MM-DD",
            )

        st.markdown("#### 🧶 도안 및 실 정보")

        pattern_source = st.text_input(
            "도안 출처",
            value=val("pattern_source"),
            placeholder="도안 링크, 책 제목, 제작자 등",
        )

        col1, col2 = st.columns(2)

        with col1:
            yarn_options = options_for("실 종류", val("yarn_type"))
            yarn_type = st.selectbox(
                "실 종류",
                yarn_options,
                index=(
                    yarn_options.index(val("yarn_type"))
                    if val("yarn_type") in yarn_options else 0
                ),
            )

        with col2:
            color_options = options_for("실 색상", val("yarn_color"))
            yarn_color = st.selectbox(
                "실 색상",
                color_options,
                index=(
                    color_options.index(val("yarn_color"))
                    if val("yarn_color") in color_options else 0
                ),
            )

        yarn_info = st.text_input(
            "실 상세 정보",
            value=val("yarn_info"),
            placeholder="브랜드, 제품명, 굵기, 사용량 등",
        )

        st.markdown("#### 🪡 바늘 정보")

        col1, col2 = st.columns(2)

        with col1:
            needle_options = options_for("바늘 종류", val("needle_type"))
            needle_type = st.selectbox(
                "바늘 종류",
                needle_options,
                index=(
                    needle_options.index(val("needle_type"))
                    if val("needle_type") in needle_options else 0
                ),
            )

        with col2:
            needle_size = st.text_input(
                "바늘 크기",
                value=val("needle_size"),
                placeholder="예: 3.5mm",
            )

        st.markdown("#### 📏 게이지 및 완성 정보")

        gauge_original = st.text_input(
            "원래 게이지",
            value=val("gauge_original"),
            placeholder="예: 10cm × 10cm, 20코 × 25단",
        )

        col1, col2 = st.columns(2)

        with col1:
            gauge_before = st.text_input(
                "세탁 전 게이지",
                value=val("gauge_before"),
                placeholder="예: 20코 × 25단",
            )

        with col2:
            gauge_after = st.text_input(
                "세탁 후 게이지",
                value=val("gauge_after"),
                placeholder="예: 19코 × 24단",
            )

        col1, col2 = st.columns(2)

        with col1:
            finished_size = st.text_input(
                "완성 크기",
                value=val("finished_size"),
                placeholder="예: 가로 20cm × 세로 25cm",
            )

        with col2:
            weight = st.text_input(
                "사용 무게",
                value=val("weight"),
                placeholder="예: 120g",
            )

        st.markdown("#### 📝 작업 메모")

        memo = st.text_area(
            "메모",
            value=val("memo") or val("content"),
            placeholder="사용한 기법, 어려웠던 점, 다음에 바꾸고 싶은 점 등을 적어 보세요.",
            height=130,
        )

        submitted = st.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None

    if not project.strip():
        st.warning("작품명을 입력해 주세요.")
        return None

    if finish_date and finish_date < start_date:
        st.warning("완성일은 시작일보다 빠를 수 없어요.")
        return None

    return {
        "project": project.strip(),
        "content": memo.strip(),
        "kind": kind,
        "status": status,
        "start_date": str(start_date) if start_date else None,
        "finish_date": str(finish_date) if finish_date else None,
        "pattern_source": pattern_source.strip(),
        "yarn_type": yarn_type,
        "yarn_color": yarn_color,
        "yarn_info": yarn_info.strip(),
        "needle_type": needle_type,
        "needle_size": needle_size.strip(),
        "gauge_original": gauge_original.strip(),
        "gauge_before": gauge_before.strip(),
        "gauge_after": gauge_after.strip(),
        "finished_size": finished_size.strip(),
        "weight": weight.strip(),
        "memo": memo.strip(),
    }


# --------------------------------------------------
# 6. 노션 스타일 상단 메뉴
# --------------------------------------------------

tab_records, tab_add, tab_options = st.tabs(
    ["📚 내 작품", "＋ 새 작품", "⚙️ 옵션 관리"]
)


# --------------------------------------------------
# 7. 작품 목록 및 상세 페이지
# --------------------------------------------------

with tab_records:
    records = get_records()

    filter_status = st.selectbox(
        "진행 상태별 보기",
        ["전체"] + options_for("상태"),
        key="filter_record_status",
    )

    if filter_status != "전체":
        records = [
            row for row in records
            if row["status"] == filter_status
        ]

    st.caption(f"작품 {len(records)}개")

    if not records:
        st.info("아직 기록한 작품이 없어요. '새 작품'에서 첫 기록을 추가해 보세요.")
    else:
        for row in records:
            record = dict(row)
            title = record.get("project") or "이름 없는 작품"
            status_text = record.get("status") or "상태 미설정"

            with st.expander(f"🧶 {title}　·　{status_text}"):
                st.markdown(f"### {title}")
                st.caption(
                    f"종류: {record.get('kind') or '-'}　"
                    f"| 상태: {status_text}"
                )

                st.divider()
                st.markdown("**도안 및 재료**")

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown(
                        f"<span class='property-label'>도안 출처</span><br>"
                        f"{record.get('pattern_source') or '-'}",
                        unsafe_allow_html=True,
                    )
                    st.write(f"**실 종류:** {record.get('yarn_type') or '-'}")
                    st.write(f"**실 색상:** {record.get('yarn_color') or '-'}")
                    st.write(f"**실 정보:** {record.get('yarn_info') or '-'}")

                with c2:
                    st.write(f"**바늘 종류:** {record.get('needle_type') or '-'}")
                    st.write(f"**바늘 크기:** {record.get('needle_size') or '-'}")
                    st.write(f"**시작일:** {record.get('start_date') or '-'}")
                    st.write(f"**완성일:** {record.get('finish_date') or '-'}")

                st.divider()
                st.markdown("**게이지 및 완성 정보**")

                c1, c2 = st.columns(2)

                with c1:
                    st.write(
                        f"**원래 게이지:** {record.get('gauge_original') or '-'}"
                    )
                    st.write(
                        f"**세탁 전 게이지:** {record.get('gauge_before') or '-'}"
                    )
                    st.write(
                        f"**세탁 후 게이지:** {record.get('gauge_after') or '-'}"
                    )

                with c2:
                    st.write(
                        f"**완성 크기:** {record.get('finished_size') or '-'}"
                    )
                    st.write(f"**사용 무게:** {record.get('weight') or '-'}")

                st.divider()
                st.markdown("**작업 메모**")
                st.write(record.get("memo") or "-")

                st.caption(
                    f"최초 기록: {record.get('created_at') or '-'}"
                    f"　·　최근 수정: {record.get('updated_at') or '-'}"
                )

                st.divider()

                with st.expander("✏️ 작품 정보 수정"):
                    edited = render_record_form(
                        f"edit_record_{record['id']}",
                        old=record,
                        submit_label="수정 내용 한 번에 저장",
                    )

                    if edited is not None:
                        try:
                            save_record(edited, record_id=record["id"])
                            st.success("작품 정보를 수정했어요.")
                            st.rerun()
                        except Exception as error:
                            st.error("수정 중 오류가 발생했어요.")
                            st.exception(error)

                with st.expander("🗑️ 작품 삭제"):
                    st.warning("삭제한 작품 기록은 복구하기 어려울 수 있어요.")
                    confirm = st.checkbox(
                        "이 작품 기록을 삭제하겠습니다.",
                        key=f"confirm_delete_{record['id']}",
                    )

                    if st.button(
                        "작품 기록 삭제",
                        key=f"delete_record_{record['id']}",
                        disabled=not confirm,
                    ):
                        try:
                            ex(
                                """
                                DELETE FROM records
                                WHERE id = :id AND nick = :nick
                                """,
                                {"id": record["id"], "nick": nick},
                            )
                            st.success("작품 기록을 삭제했어요.")
                            st.rerun()
                        except Exception as error:
                            st.error("삭제 중 오류가 발생했어요.")
                            st.exception(error)


# --------------------------------------------------
# 8. 새 작품 등록: 전체 항목을 한 번에 저장
# --------------------------------------------------

with tab_add:
    st.markdown("### ＋ 새 작품 추가")
    st.caption(
        "필요한 정보를 입력한 다음 화면 맨 아래의 저장 버튼을 한 번만 눌러 주세요."
    )

    new_values = render_record_form("new_record_form")

    if new_values is not None:
        try:
            save_record(new_values)

            # 하루 한 번만 기록 작성 포인트 지급
            award_points(
                nick,
                f"record-day:{now().date().isoformat()}",
                5,
                "뜨개 기록장 작성",
            )

            st.success("작품 정보가 모두 저장됐어요! 🧶")
            st.rerun()

        except Exception as error:
            st.error("작품 저장 중 오류가 발생했어요.")
            st.exception(error)


# --------------------------------------------------
# 9. 사용자 지정 옵션 관리
# --------------------------------------------------

with tab_options:
    st.markdown("### ⚙️ 나만의 뜨개 옵션")
    st.caption(
        "종류, 상태, 실 종류, 실 색상, 바늘 종류를 직접 추가하거나 관리할 수 있어요."
    )

    category = st.selectbox(
        "관리할 항목",
        list(DEFAULT_OPTIONS.keys()),
        key="manage_category",
    )

    current_options = options_for(category)

    st.markdown("**현재 사용할 수 있는 옵션**")
    st.write("　·　".join(current_options))

    with st.form("add_option_form", clear_on_submit=True):
        new_option = st.text_input(
            "추가할 옵션 이름",
            placeholder="예: 양말, 리본실, 대나무 코바늘",
        )
        add_clicked = st.form_submit_button("옵션 추가")

    if add_clicked:
        clean_option = new_option.strip()

        if not clean_option:
            st.warning("옵션 이름을 입력해 주세요.")
        elif clean_option in current_options:
            st.info("이미 존재하는 옵션이에요.")
        elif add_record_option(nick, category, clean_option):
            st.success("옵션을 추가했어요.")
            st.rerun()
        else:
            st.error("옵션 추가에 실패했어요.")

    st.divider()
    st.markdown("#### 사용자 지정 옵션 수정 및 삭제")

    saved_options = q(
        """
        SELECT id, option_value
        FROM record_options
        WHERE nick = :nick AND category = :category
        ORDER BY id
        """,
        {"nick": nick, "category": category},
    )

    if saved_options:
        saved_values = [row["option_value"] for row in saved_options]

        selected_old = st.selectbox(
            "수정하거나 삭제할 옵션",
            saved_values,
            key="selected_custom_option",
        )

        new_name = st.text_input(
            "변경할 이름",
            value=selected_old,
            key="renamed_custom_option",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("이름 변경", use_container_width=True):
                clean_name = new_name.strip()

                if not clean_name:
                    st.warning("새 이름을 입력해 주세요.")
                elif (
                    clean_name in current_options
                    and clean_name != selected_old
                ):
                    st.warning("이미 존재하는 옵션 이름이에요.")
                elif rename_record_option(
                    nick, category, selected_old, clean_name
                ):
                    st.success("옵션 이름을 변경했어요.")
                    st.rerun()
                else:
                    st.error("이름 변경에 실패했어요.")

        with col2:
            if st.button("옵션 삭제", use_container_width=True):
                if delete_record_option(nick, category, selected_old):
                    st.success("옵션을 삭제했어요.")
                    st.rerun()
                else:
                    st.error("옵션 삭제에 실패했어요.")
    else:
        st.info("아직 직접 추가한 옵션이 없어요.")

# --------------------------------------------------
# 새 작품 등록 + 포인트 지급
# --------------------------------------------------

with tab_add:
    st.markdown("### ＋ 새 작품 추가")
    st.caption(
        "필요한 정보를 입력한 다음 저장 버튼을 한 번만 눌러 주세요."
    )

    new_values = render_record_form("new_record_form")

    if new_values is not None:
        try:
            # 1. 작품 기록 저장
            save_record(new_values)

            # 2. 오늘 날짜를 기준으로 보상 키 생성
            today_key = now().date().isoformat()
            reward_key = f"record-day:{today_key}"

            # 3. 포인트 지급 결과 확인
            rewarded = award_points(
                nick,
                reward_key,
                5,
                "뜨개 기록장 작성",
            )

            if rewarded:
                st.success("작품 기록 저장 완료! 포인트 5P를 받았어요. 🧶")
            else:
                st.success("작품 기록을 저장했어요!")
                st.info(
                    "오늘의 뜨개 기록 작성 포인트는 이미 받았거나 "
                    "포인트 지급에 실패했을 수 있어요."
                )

            st.rerun()

        except Exception as error:
            st.error("기록 저장 또는 포인트 처리 중 오류가 발생했어요.")
            st.exception(error)
