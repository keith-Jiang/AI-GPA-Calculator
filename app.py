import io
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_extractor import extract_courses
from gpa_standards import (
    ALL_STANDARD_NAMES,
    GRADE_STANDARD_NAMES,
    SCORE_STANDARD_NAMES,
    calculate_weighted_gpa,
    is_invalid_grade,
)

load_dotenv()

st.set_page_config(page_title="AI 绩点计算器", page_icon="🎓", layout="wide")

# ── Sidebar: API 配置 ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input(
        "OpenRouter API Key",
        value=os.getenv("OPENROUTER_API_KEY", ""),
        type="password",
        help="从 https://openrouter.ai/keys 获取",
    )
    st.divider()
    st.caption("数据不存储在服务端，仅通过 API 临时处理。")

# ── 主页面 ──────────────────────────────────────────────────────────

st.title("🎓 AI 绩点计算器")
st.markdown("上传成绩单图片或 PDF → AI 自动提取 → 选择绩点标准 → 一键计算 GPA")

# ── Step 1: 上传文件 ───────────────────────────────────────────────

st.header("① 上传成绩单")

uploaded = st.file_uploader(
    "支持 JPG / PNG / PDF 格式",
    type=["jpg", "jpeg", "png", "pdf"],
    key="file_uploader",
)

if uploaded:
    if uploaded.type == "application/pdf":
        st.info(f"已上传 PDF: **{uploaded.name}** ({uploaded.size / 1024:.1f} KB)")
    else:
        st.image(uploaded, caption="成绩单预览", use_container_width=True)

# ── Step 2: AI 提取 + 用户校验 ─────────────────────────────────────

st.header("② 提取课程信息")

col_extract, col_manual = st.columns(2)

with col_extract:
    extract_btn = st.button(
        "🤖 AI 提取", disabled=not uploaded or not api_key, use_container_width=True
    )

with col_manual:
    manual_btn = st.button("✏️ 手动输入", use_container_width=True)

if extract_btn and uploaded and api_key:
    with st.spinner("正在调用 AI 提取课程信息…"):
        try:
            file_bytes = uploaded.getvalue()
            courses = extract_courses(file_bytes, uploaded.type, api_key)
            st.session_state["courses"] = courses
            st.session_state["extract_done"] = True
            st.success(f"成功提取 {len(courses)} 门课程！请检查下方数据。")
        except Exception as e:
            st.error(f"提取失败: {e}")

if manual_btn:
    st.session_state["courses"] = [
        {"course": "", "credits": 0.0, "score": "", "uncertain": False}
    ]
    st.session_state["extract_done"] = True

if st.session_state.get("extract_done"):
    courses_raw = st.session_state.get("courses", [])
    df = pd.DataFrame(courses_raw)

    if "uncertain" in df.columns:
        has_uncertain = df["uncertain"].any()
        display_df = df.drop(columns=["uncertain"])
    else:
        has_uncertain = False
        display_df = df.copy()

    display_df.columns = ["课程名称", "学分", "成绩"]
    display_df["成绩"] = display_df["成绩"].astype(str)

    invalid_count = display_df["成绩"].apply(is_invalid_grade).sum()

    if has_uncertain:
        st.warning("⚠️ 部分课程 AI 提取结果不太确定，请重点检查。")
    if invalid_count > 0:
        st.info(f"检测到 {invalid_count} 门课程为无效等级（如 P/W/EX 等），将自动排除不计入 GPA。")

    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        key="course_editor",
    )

    st.session_state["edited_df"] = edited_df

# ── Step 3: 绩点计算 ──────────────────────────────────────────────

st.header("③ 计算绩点")

if st.session_state.get("edited_df") is not None:
    edited_df: pd.DataFrame = st.session_state["edited_df"]
    valid_df = edited_df.dropna(subset=["课程名称", "学分", "成绩"])
    valid_df = valid_df[valid_df["课程名称"].astype(str).str.strip() != ""]

    if valid_df.empty:
        st.warning("请先填写至少一门课程的信息。")
    else:
        courses_for_calc = [
            {"course": row["课程名称"], "credits": row["学分"], "score": str(row["成绩"])}
            for _, row in valid_df.iterrows()
        ]

        score_type = st.radio(
            "成绩类型",
            ["百分制", "等级制"],
            horizontal=True,
            help="百分制：成绩为 0-100 的数字；等级制：成绩为 A+/B-/C 等字母等级",
        )
        is_grade_mode = score_type == "等级制"

        tab_single, tab_compare = st.tabs(["📊 单标准计算", "📋 多标准对比"])

        # ── 单标准模式 ──
        with tab_single:
            if is_grade_mode:
                standard = st.selectbox("选择等级制绩点标准", GRADE_STANDARD_NAMES)
                custom_ranges = None
            else:
                standard = st.selectbox(
                    "选择百分制绩点标准", SCORE_STANDARD_NAMES + ["自定义"]
                )
                custom_ranges = None
                if standard == "自定义":
                    st.markdown("请定义你的绩点分数段（从高到低）：")
                    custom_df = st.data_editor(
                        pd.DataFrame({
                            "最低分": [90, 80, 70, 60, 0],
                            "最高分": [100, 89, 79, 69, 59],
                            "绩点": [4.0, 3.0, 2.0, 1.0, 0.0],
                        }),
                        num_rows="dynamic",
                        use_container_width=True,
                        key="custom_standard_editor",
                    )
                    custom_ranges = [
                        (row["最低分"], row["最高分"], row["绩点"])
                        for _, row in custom_df.iterrows()
                    ]

            result = calculate_weighted_gpa(
                courses_for_calc,
                standard,
                is_grade_mode=is_grade_mode,
                custom_ranges=custom_ranges,
            )

            result_df = pd.DataFrame(result["courses"])
            result_df = result_df.rename(columns={
                "course": "课程名称",
                "credits": "学分",
                "score": "成绩",
                "gpa": "绩点",
                "excluded": "已排除",
            })

            # 添加"选中"列：无效/排除的课程默认不选中
            result_df.insert(0, "选中", ~result_df["已排除"])

            select_df = st.data_editor(
                result_df,
                disabled=["课程名称", "学分", "成绩", "绩点", "已排除"],
                use_container_width=True,
                hide_index=True,
                key="select_editor",
            )

            # 根据选中状态重新计算 GPA
            selected_rows = select_df[select_df["选中"] & ~select_df["已排除"]]
            if not selected_rows.empty:
                total_credits = selected_rows["学分"].astype(float).sum()
                total_weighted = (
                    selected_rows["学分"].astype(float) * selected_rows["绩点"].astype(float)
                ).sum()
                final_gpa = round(total_weighted / total_credits, 4) if total_credits > 0 else 0.0
            else:
                final_gpa = 0.0

            col_gpa, col_info = st.columns([1, 2])
            with col_gpa:
                st.metric("加权平均绩点 (GPA)", f"{final_gpa:.4f}")
            with col_info:
                total = len(select_df)
                selected = int(selected_rows.shape[0])
                excluded = int(select_df["已排除"].sum())
                st.caption(
                    f"共 {total} 门课 · 已选中 {selected} 门 · "
                    f"自动排除 {excluded} 门（无效等级）"
                )

        # ── 多标准对比模式 ──
        with tab_compare:
            st.markdown("一键对比所有内置标准下的 GPA：")

            # 用选中的课程做对比
            selected_courses = [
                {"course": row["课程名称"], "credits": row["学分"], "score": str(row["成绩"])}
                for _, row in selected_rows.iterrows()
            ] if not selected_rows.empty else []

            if not selected_courses:
                st.warning("请至少选中一门课程。")
            else:
                if is_grade_mode:
                    compare_standards = GRADE_STANDARD_NAMES
                else:
                    compare_standards = SCORE_STANDARD_NAMES

                compare_data = []
                for std_name in compare_standards:
                    r = calculate_weighted_gpa(
                        selected_courses, std_name, is_grade_mode=is_grade_mode
                    )
                    compare_data.append({
                        "绩点标准": std_name,
                        "加权平均GPA": round(r["gpa"], 4),
                    })

                compare_df = pd.DataFrame(compare_data)
                st.dataframe(compare_df, use_container_width=True, hide_index=True)
                st.bar_chart(compare_df.set_index("绩点标准"))

        # ── 导出 CSV ──
        st.divider()
        export_df = select_df[["课程名称", "学分", "成绩", "绩点", "选中", "已排除"]]
        csv_buf = io.StringIO()
        export_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "📥 导出为 CSV",
            data=csv_buf.getvalue(),
            file_name="gpa_result.csv",
            mime="text/csv",
        )
else:
    st.info("请先上传成绩单并完成课程信息提取。")
