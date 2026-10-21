# common.py
# 공통 데이터베이스 기능 + 뜨개 기록 옵션 관리

import streamlit as st
import html
import json


# 기존 프로젝트의 데이터베이스 연결 함수 q(), ex(), setup()은 유지한다.
# q(sql, params=()) : 조회 결과 반환
# ex(sql, params=()) : SQL 실행


def esc(value):
    """HTML에 표시할 문자열을 안전하게 변환."""
    return html.escape(str(value or ""))


def init_record_options():
    """사용자 지정 옵션을 영구 저장하는 테이블 생성."""

    ex("""
        CREATE TABLE IF NOT EXISTS record_options (
            id INTEGER PRIMARY KEY,
            nick TEXT NOT NULL,
            category TEXT NOT NULL,
            option_value TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 같은 사용자·분류 안에서 옵션 중복 저장 방지
    ex("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_record_options_unique
        ON record_options (nick, category, option_value)
    """)


def get_record_options(nick, category, defaults=None):
    """
    데이터베이스에서 저장된 옵션을 불러온다.
    기본 옵션과 사용자가 추가한 옵션을 합쳐 반환한다.
    """
    defaults = defaults or []

    rows = q(
        """
        SELECT option_value
        FROM record_options
        WHERE nick = ?
        AND category = ?
        ORDER BY id
        """,
        (nick, category),
    )

    saved = [str(row["option_value"]) for row in rows]
    result = []

    for value in list(defaults) + saved:
        if value and value not in result:
            result.append(value)

    return result


def add_record_option(nick, category, value):
    """사용자 옵션 추가."""
    value = str(value).strip()

    if not value:
        return False

    try:
        ex(
            """
            INSERT INTO record_options
                (nick, category, option_value)
            VALUES (?, ?, ?)
            """,
            (nick, category, value),
        )
        return True

    except Exception:
        # 중복 옵션 등으로 저장되지 않은 경우
        return False


def rename_record_option(nick, category, old_value, new_value):
    """사용자 옵션 이름 수정."""
    old_value = str(old_value).strip()
    new_value = str(new_value).strip()

    if not old_value or not new_value:
        return False

    if old_value == new_value:
        return True

    try:
        ex(
            """
            UPDATE record_options
            SET option_value = ?
            WHERE nick = ?
              AND category = ?
              AND option_value = ?
            """,
            (new_value, nick, category, old_value),
        )
        return True

    except Exception:
        return False


def delete_record_option(nick, category, value):
    """사용자 옵션 삭제."""
    ex(
        """
        DELETE FROM record_options
        WHERE nick = ?
          AND category = ?
          AND option_value = ?
        """,
        (nick, category, value),
    )


def init_record_options_once():
    """Streamlit에서 옵션 테이블을 최초 1회 준비."""
    if not st.session_state.get("_record_options_initialized"):
        init_record_options()
        st.session_state["_record_options_initialized"] = True
