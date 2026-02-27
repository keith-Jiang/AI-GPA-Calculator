GPA_STANDARDS = {
    "标准4.0": [
        (90, 100, 4.0),
        (80, 89, 3.0),
        (70, 79, 2.0),
        (60, 69, 1.0),
        (0, 59, 0.0),
    ],
    "改进4.0(1)": [
        (85, 100, 4.0),
        (70, 84, 3.0),
        (60, 69, 2.0),
        (0, 59, 0.0),
    ],
    "改进4.0(2)": [
        (85, 100, 4.0),
        (75, 84, 3.0),
        (60, 74, 2.0),
        (0, 59, 0.0),
    ],
    "北大4.0": [
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
    "加拿大4.3": [
        (90, 100, 4.3),
        (85, 89, 4.0),
        (80, 84, 3.7),
        (75, 79, 3.3),
        (70, 74, 3.0),
        (65, 69, 2.7),
        (60, 64, 2.3),
        (0, 59, 0.0),
    ],
}

STANDARD_NAMES = list(GPA_STANDARDS.keys())


def _score_to_gpa_5(score: float) -> float:
    """标准5.0: GPA = (score - 50) / 10, 不及格为 0"""
    if score < 60:
        return 0.0
    return round((score - 50) / 10, 2)


def score_to_gpa(score: float, standard: str, custom_ranges: list | None = None) -> float:
    """将百分制成绩转换为绩点。

    Args:
        score: 百分制成绩 (0-100)
        standard: 绩点标准名称
        custom_ranges: 自定义标准时的区间列表 [(min, max, gpa), ...]
    """
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


def calculate_weighted_gpa(
    courses: list[dict], standard: str, custom_ranges: list | None = None
) -> dict:
    """计算加权平均绩点。

    Args:
        courses: [{"course": str, "credits": float, "score": float}, ...]
        standard: 绩点标准名称
        custom_ranges: 自定义标准时的区间列表

    Returns:
        {"courses": [带绩点的课程列表], "gpa": 加权平均绩点}
    """
    total_credits = 0.0
    total_weighted = 0.0
    result_courses = []

    for c in courses:
        credits = float(c["credits"])
        score = float(c["score"])
        gpa = score_to_gpa(score, standard, custom_ranges)
        total_credits += credits
        total_weighted += credits * gpa
        result_courses.append({**c, "gpa": gpa})

    weighted_gpa = round(total_weighted / total_credits, 4) if total_credits > 0 else 0.0
    return {"courses": result_courses, "gpa": weighted_gpa}


ALL_STANDARD_NAMES = STANDARD_NAMES + ["标准5.0"]
