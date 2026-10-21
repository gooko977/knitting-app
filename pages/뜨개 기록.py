import streamlit as st

from common import setup, header, q, engine, records, now, check_text, award_points

setup()
nick = st.session_state.nick
header("나의 뜨개 기록장", "작품의 시작부터 완성까지 기록해 봐.")

st.caption("작품명, 사용한 실과 바늘, 게이지, 작업 과정 등을 기록할 수 있어.")

with st.expander("＋ 새 작품 기록하기", expanded=False):
    with st.form("new_record_form", clear_on_submit=True):
        project = st.text_input(
            "작품명",
            max_chars=80,
            placeholder="예: 크림 피치 미니 가방",
        )
        content = st.text_area(
            "작품 기록",
            max_chars=3000,
            placeholder=(
                "사용한 실과 바늘, 게이지, 작업 과정, "
                "다음에 수정하고 싶은 점 등을 적어 줘."
            ),
        )
        submitted = st.form_submit_button("작품 저장", type="primary")

    if submitted:
        valid, clean_project = check_text(project, 80)

        if not valid:
            st.warning("작품명을 입력해 줘.")
        else:
            try:
                with engine.begin() as conn:
                    result = conn.execute(
                        records.insert().values(
                            nick=nick,
                            record_date=now().date().isoformat(),
                            project=clean_project,
                            content=content.strip(),
                            created_at=now(),
                        )
                    )
                    record_id = result.inserted_primary_key[0]

                # 같은 닉네임은 하루에 한 번만 기록장 보상
                reward_key = f"record-day:{now().date().isoformat()}"
                awarded = award_points(
                    nick,
                    reward_key,
                    5,
                    "뜨개 기록장 작성",
                )

                if awarded:
                    st.success("작품을 저장했어! +5P")
                else:
                    st.success("작품을 저장했어! 오늘의 기록장 포인트는 이미 받았어.")

                st.rerun()

            except Exception as error:
                st.error("작품 저장에 실패했어. 잠시 후 다시 시도해 줘.")
                st.caption(f"오류 유형: {type(error).__name__}")

st.divider()
st.subheader("내 작품 목록")

projects = q(
    """
    SELECT id, record_date, project, content, created_at
    FROM records
    WHERE nick = :nick
    ORDER BY id DESC
    LIMIT 100
    """,
    {"nick": nick},
)

if not projects:
    st.info("아직 기록한 작품이 없어. 첫 작품을 등록해 봐!")
else:
    for project in projects:
        with st.container(border=True):
            st.markdown(f"### 🧶 {project['project']}")
            st.caption(
                f"기록일: {project['record_date']} · "
                f"등록 시각: {project['created_at']}"
            )
            st.write(project["content"] or "추가 메모가 없어.")

            with st.expander("기록 수정하기"):
                with st.form(f"edit_record_{project['id']}"):
                    new_title = st.text_input(
                        "작품명",
                        value=project["project"],
                        max_chars=80,
                    )
                    new_content = st.text_area(
                        "작품 기록",
                        value=project["content"] or "",
                        max_chars=3000,
                    )
                    save_edit = st.form_submit_button("수정 저장")

                if save_edit:
                    valid, clean_title = check_text(new_title, 80)

                    if not valid:
                        st.warning("작품명을 확인해 줘.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(
                                    records.update()
                                    .where(
                                        records.c.id == project["id"],
                                        records.c.nick == nick,
                                    )
                                    .values(
                                        project=clean_title,
                                        content=new_content.strip(),
                                    )
                                )

                            st.success("기록을 수정했어. 수정 보상은 지급되지 않아.")
                            st.rerun()

                        except Exception:
                            st.error("수정에 실패했어.")
