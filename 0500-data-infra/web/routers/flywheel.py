"""数据飞轮 API"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/flywheel", tags=["flywheel"])


class FlywheelRunRequest(BaseModel):
    model_id: Optional[str] = None        # 待改进模型（缺省取最新）
    output_model_id: Optional[str] = None # 训练产出模型名（模拟训练时使用）
    task_filter: Optional[List[str]] = None


class FlywheelEvalRequest(BaseModel):
    model_id: str
    task_name: str
    num_trials: int = Field(..., gt=0)
    success_count: int = Field(..., ge=0)
    robot_id: str = ""
    environment: str = ""


@router.get("/history")
def history(request: Request):
    """历史飞轮迭代报告"""
    state = request.app.state.app_state
    return [r.to_dict() for r in state.flywheel.history()]


@router.get("/state")
def flywheel_state(request: Request):
    """飞轮当前状态（开放失败 Case / 低成功率任务）"""
    state = request.app.state.app_state
    model_id = state.latest_model_id()
    return {
        "latest_model": model_id,
        "open_cases": len(state.registry.list_failures(status="open")),
        "low_success_tasks": state.registry.low_success_tasks(model_id, threshold=0.5)
        if model_id else [],
        "episode_count": len(state.load_all_episodes()),
    }


@router.post("/run")
def run_flywheel(request: Request, req: FlywheelRunRequest):
    """执行一轮飞轮（模拟训练/评估），返回迭代报告"""
    state = request.app.state.app_state
    model_id = req.model_id or state.latest_model_id()
    if not model_id:
        raise HTTPException(status_code=400, detail="尚无模型，无法运行飞轮")

    episode_lookup = state.load_all_episodes()
    output_model = req.output_model_id or f"{model_id}_fw"
    source_model_id = model_id

    def train_fn(dataset_version: str, job_id: str) -> str:
        return output_model

    def eval_fn(produced_model: str, task_filter=None) -> Dict[str, Any]:
        # 模拟: 新模型成功率相对来源模型提升 +0.25，上限 0.95
        # 新模型刚训练出来尚无评测记录，回退到来源模型聚合成功率
        rates = state.registry.aggregate_success_rate_by_task(produced_model)
        if not rates:
            rates = state.registry.aggregate_success_rate_by_task(source_model_id)
        result = {}
        for task, info in rates.items():
            if task_filter and task not in task_filter:
                continue
            new_rate = min(0.95, info["success_rate"] + 0.25)
            trials = max(10, info["trials"])
            result[task] = {
                "trials": trials,
                "success": int(round(new_rate * trials)),
                "success_rate": new_rate,
            }
        return result

    report = state.flywheel.run_once(
        model_id=model_id,
        episode_lookup=episode_lookup,
        task_filter=req.task_filter,
        train_fn=train_fn,
        eval_fn=eval_fn,
        new_model_id=output_model,
    )
    return report.to_dict()


@router.post("/eval")
def record_eval(request: Request, req: FlywheelEvalRequest):
    """登记一次实机评估，自动回流失败数据"""
    state = request.app.state.app_state
    ev = state.flywheel.record_real_world_eval(
        model_id=req.model_id,
        task_name=req.task_name,
        num_trials=req.num_trials,
        success_count=req.success_count,
        robot_id=req.robot_id,
        environment=req.environment,
    )
    return {
        "eval": ev.to_dict(),
        "success_rate": ev.success_rate,
        "failures_reflowed": req.num_trials - req.success_count,
    }
