"""DeepSeek client for AI task planning."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "ai.json"
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_MINUTES = 60
MAX_MINUTES = 720

_PROMPT = """你是学习任务规划助手。用户会给你一段学习/工作行程描述，请拆解成任务清单。

要求：
1. 只输出 JSON 数组，不要任何其他文字或 markdown 代码块。
2. 每个元素是对象，含两个字段：
   - "title": 任务名（简洁、具体、可直接执行）
   - "planned_minutes": 建议专注时长（正整数分钟，默认 60）
3. 合并同类小任务，拆解过大任务，使每个任务时长在 15-120 分钟之间。
4. 保持原意的先后顺序。

用户输入：
{text}

请输出 JSON 数组："""


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _extract_json(content: str) -> list:
    """Parse a JSON array from DeepSeek output, tolerating code fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("expected a JSON array")
    return data


def plan_tasks(text: str) -> list[dict]:
    """Return [{"title", "planned_minutes"}] for the given free-text schedule."""
    cfg = _load_config()
    key = cfg.get("deepseek_api_key")
    if not key:
        raise RuntimeError("missing DeepSeek API key (config/ai.json)")
    model = cfg.get("model") or DEFAULT_MODEL

    prompt = _PROMPT.format(text=text)
    resp = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "stream": False,
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text[:200]}")

    content = resp.json()["choices"][0]["message"]["content"]
    tasks: list[dict] = []
    for item in _extract_json(content):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        try:
            minutes = int(item.get("planned_minutes", DEFAULT_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_MINUTES
        minutes = max(1, min(minutes, MAX_MINUTES))
        tasks.append({"title": title, "planned_minutes": minutes})
    return tasks
