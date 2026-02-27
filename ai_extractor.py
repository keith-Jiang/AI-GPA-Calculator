import base64
import json
import re

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-3-flash-preview"

EXTRACTION_PROMPT = """\
你是一个成绩单数据提取助手。请从上传的成绩单图片或PDF中提取所有课程信息。

要求：
1. 提取每门课程的：课程名称(course)、学分(credits)、成绩(score)
2. score 字段请保留成绩单上的原始值：
   - 如果是百分制数字（如 92），直接写数字 "92"
   - 如果是等级制（如 A+、B-、P、W 等），直接写等级字符串 "A+"
   - 不要将等级转换为数字，保持原样
3. 学分必须是数字
4. 如果某个字段你不确定，将该课程的 uncertain 设为 true
5. 只返回JSON数组，不要包含任何其他文字或markdown标记

示例输出（百分制成绩单）：
[
  {"course": "高等数学", "credits": 4.0, "score": "92", "uncertain": false},
  {"course": "大学英语", "credits": 3.0, "score": "85", "uncertain": false}
]

示例输出（等级制成绩单）：
[
  {"course": "高等数学", "credits": 4.0, "score": "A+", "uncertain": false},
  {"course": "体育", "credits": 1.0, "score": "P", "uncertain": false}
]

请严格按照以上JSON格式输出。"""


def _build_content_parts(file_bytes: bytes, file_type: str) -> list[dict]:
    """构建 OpenRouter API 的 content parts。"""
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    parts: list[dict] = [{"type": "text", "text": EXTRACTION_PROMPT}]

    if file_type == "application/pdf":
        parts.append({
            "type": "file",
            "file": {
                "filename": "transcript.pdf",
                "file_data": f"data:application/pdf;base64,{b64}",
            },
        })
    else:
        mime = file_type if file_type in ("image/jpeg", "image/png", "image/webp") else "image/jpeg"
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    return parts


def _parse_json_response(text: str) -> list[dict]:
    """从 AI 响应中解析 JSON 数组，兼容 markdown code block 包裹的情况。"""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("AI 返回的不是 JSON 数组")
    return data


def extract_courses(
    file_bytes: bytes,
    file_type: str,
    api_key: str,
    max_retries: int = 2,
) -> list[dict]:
    """调用 OpenRouter API 提取成绩单中的课程信息。

    Args:
        file_bytes: 文件的二进制内容
        file_type: MIME 类型 (image/jpeg, image/png, application/pdf, ...)
        api_key: OpenRouter API Key
        max_retries: 解析失败时的最大重试次数

    Returns:
        [{"course": str, "credits": float, "score": str, "uncertain": bool}, ...]

    Raises:
        RuntimeError: API 调用或 JSON 解析在所有重试后仍失败
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": _build_content_parts(file_bytes, file_type),
            }
        ],
        "temperature": 0.1,
    }

    last_error = None
    for attempt in range(1 + max_retries):
        if attempt > 0:
            payload["temperature"] = 0.0

        resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()

        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"API 错误: {body['error']}")

        text = body["choices"][0]["message"]["content"]
        try:
            courses = _parse_json_response(text)
            for c in courses:
                c.setdefault("uncertain", False)
                c["credits"] = float(c["credits"])
                c["score"] = str(c["score"]).strip()
            return courses
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            last_error = e

    raise RuntimeError(
        f"AI 返回的数据格式无法解析（已重试 {max_retries} 次）: {last_error}"
    )
