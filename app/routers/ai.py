from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import ai_client

router = APIRouter(prefix="/api/ai", tags=["ai"])


class PlanRequest(BaseModel):
    text: str


class PlanTask(BaseModel):
    title: str
    planned_minutes: int


class PlanResponse(BaseModel):
    tasks: list[PlanTask]


@router.post("/plan", response_model=PlanResponse)
def ai_plan(body: PlanRequest):
    try:
        tasks = ai_client.plan_tasks(body.text)
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith("missing"):
            raise HTTPException(500, "请在 config/ai.json 填入 DeepSeek API Key")
        raise HTTPException(502, f"DeepSeek 调用失败: {msg}")
    except ValueError:
        raise HTTPException(400, "AI 返回格式异常，请重试或简化输入")
    return {"tasks": tasks}
