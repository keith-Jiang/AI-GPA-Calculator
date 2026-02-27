# ── 百分制 → 绩点 标准 (min_score, max_score, gpa) ──────────────────

GPA_STANDARDS = {
    "标准百分制4.0": [
        (90, 100, 4.0),
        (80, 89, 3.0),
        (70, 79, 2.0),
        (60, 69, 1.0),
        (0, 59, 0.0),
    ],
    "改进百分制4.0(1)": [
        (85, 100, 4.0),
        (70, 84, 3.0),
        (60, 69, 2.0),
        (0, 59, 0.0),
    ],
    "改进百分制4.0(2)": [
        (85, 100, 4.0),
        (75, 84, 3.0),
        (60, 74, 2.0),
        (0, 59, 0.0),
    ],
    "北大百分制4.0": [
        (90, 100, 4.0),
        (85, 89, 3.7),
        (82, 84, 3.3),
        (78, 81, 3.0),
        (75, 77, 2.7),
        (72, 74, 2.3),
        (68, 71, 2.0),
        (64, 67, 1.5),
        (60, 63, 1.0),
        (0, 59, 0.0),
    ],
    "加拿大百分制4.3": [
        (90, 100, 4.3),
        (85, 89, 4.0),
        (80, 84, 3.7),
        (75, 79, 3.3),
        (70, 74, 3.0),
        (65, 69, 2.7),
        (60, 64, 2.3),
        (0, 59, 0.0),
    ],
    "中科大百分制4.3": [
        (95, 100, 4.3),
        (90, 94, 4.0),
        (85, 89, 3.7),
        (82, 84, 3.3),
        (78, 81, 3.0),
        (75, 77, 2.7),
        (72, 74, 2.3),
        (68, 71, 2.0),
        (65, 67, 1.7),
        (64, 64, 1.5),
        (61, 63, 1.3),
        (60, 60, 1.0),
        (0, 59, 0.0),
    ],
    "上海交大百分制4.3": [
        (95, 100, 4.3),
        (90, 94, 4.0),
        (85, 89, 3.7),
        (80, 84, 3.3),
        (75, 79, 3.0),
        (70, 74, 2.7),
        (67, 69, 2.3),
        (65, 66, 2.0),
        (62, 64, 1.7),
        (60, 61, 1.0),
        (0, 59, 0.0),
    ],
}

SCORE_STANDARD_NAMES = list(GPA_STANDARDS.keys()) + ["标准5.0"]

# ── 等级制 → 绩点 标准 ──────────────────────────────────────────────

GRADE_STANDARDS = {
    "北大等级制4.0": {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0,
        "F": 0.0,
    },
    "美国等级制4.0": {
        "A+": 4.0, "A": 4.0, "A-": 3.7, "AB": 3.5,
        "B+": 3.3, "B": 3.0, "B-": 2.7, "BC": 2.5,
        "C+": 2.3, "C": 2.0, "C-": 1.7, "CD": 1.5,
        "D+": 1.3, "D": 1.0, "D-": 0.7,
        "F": 0.0,
    },
}

GRADE_STANDARD_NAMES = list(GRADE_STANDARDS.keys())

# ── 无效等级（不计入 GPA） ──────────────────────────────────────────

INVALID_GRADES = {
    "EX", "IP", "I", "P", "NP", "W",
    "通过", "不通过", "合格", "不合格", "免修", "退课",
}

# ── 合并导出名 ──────────────────────────────────────────────────────

ALL_STANDARD_NAMES = SCORE_STANDARD_NAMES  # 向后兼容


# ── 工具函数 ────────────────────────────────────────────────────────

def is_invalid_grade(score_str: str) -> bool:
    """判断成绩是否为不计入 GPA 的无效等级。"""
    return str(score_str).strip().upper() in {g.upper() for g in INVALID_GRADES}


def is_grade_input(score_str: str) -> bool:
    """判断成绩字符串是等级制（True）还是百分制数字（False）。"""
    s = str(score_str).strip()
    try:
        float(s)
        return False
    except ValueError:
        return True


def _score_to_gpa_5(score: float) -> float:
    """标准5.0: GPA = (score - 50) / 10, 不及格为 0"""
    if score < 60:
        return 0.0
    return round((score - 50) / 10, 2)


def score_to_gpa(score: float, standard: str, custom_ranges: list | None = None) -> float:
    """将百分制成绩转换为绩点。"""
    if standard == "标准5.0":
        return _score_to_gpa_5(score)

    ranges = custom_ranges if standard == "自定义" else GPA_STANDARDS.get(standard)
    if not ranges:
        raise ValueError(f"未知的绩点标准: {standard}")

    score = round(score)
    for low, high, gpa in ranges:
        if low <= score <= high:
            return gpa
    return 0.0


def grade_to_gpa(grade: str, standard: str) -> float | None:
    """将等级制成绩转换为绩点。找不到映射时返回 None。"""
    mapping = GRADE_STANDARDS.get(standard)
    if not mapping:
        raise ValueError(f"未知的等级制标准: {standard}")
    normalized = grade.strip().upper()
    for key, gpa in mapping.items():
        if key.upper() == normalized:
            return gpa
    return None


def calculate_weighted_gpa(
    courses: list[dict],
    standard: str,
    *,
    is_grade_mode: bool = False,
    custom_ranges: list | None = None,
) -> dict:
    """计算加权平均绩点，支持百分制和等级制，自动排除无效等级。

    Args:
        courses: [{"course": str, "credits": float, "score": str, ...}, ...]
        standard: 绩点标准名称
        is_grade_mode: True 时用等级制映射，False 时用百分制映射
        custom_ranges: 自定义百分制标准的区间列表

    Returns:
        {"courses": [带 gpa 和 excluded 字段的课程列表], "gpa": 加权平均绩点}
    """
    total_credits = 0.0
    total_weighted = 0.0
    result_courses = []

    for c in courses:
        credits = float(c["credits"])
        score_str = str(c["score"]).strip()
        excluded = False
        gpa = 0.0

        if is_invalid_grade(score_str):
            excluded = True
        elif is_grade_mode:
            result = grade_to_gpa(score_str, standard)
            if result is None:
                excluded = True
            else:
                gpa = result
        else:
            try:
                gpa = score_to_gpa(float(score_str), standard, custom_ranges)
            except (ValueError, TypeError):
                excluded = True

        if not excluded:
            total_credits += credits
            total_weighted += credits * gpa

        result_courses.append({**c, "gpa": gpa, "excluded": excluded})

    weighted_gpa = round(total_weighted / total_credits, 4) if total_credits > 0 else 0.0
    return {"courses": result_courses, "gpa": weighted_gpa}
