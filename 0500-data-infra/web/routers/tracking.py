"""训练评估关联管理 API"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...tracking.models import FailureCase, FailureStatus

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


class FailureCreateRequest(BaseModel):
    task_name: str
    model_id: str = ""
    episode_id: str = ""
    robot_id: str = ""
    failure_type: str = "unknown"
    description: str = ""
    priority: int = Field(3, ge=1, le=5)


@router.get("/models")
def list_models(request: Request):
    state = request.app.state.app_state
    return [m.to_dict() for m in state.registry.list_models()]


@router.get("/jobs")
def list_jobs(request: Request, dataset_version: Optional[str] = None):
    state = request.app.state.app_state
    return [j.to_dict() for j in state.registry.list_jobs(dataset_version)]


@router.get("/benchmarks")
def list_benchmarks(request: Request, model_id: Optional[str] = None):
    state = request.app.state.app_state
    return [b.to_dict() for b in state.registry.list_benchmarks(model_id)]


@router.get("/evals")
def list_evals(request: Request, model_id: Optional[str] = None, task_name: Optional[str] = None):
    state = request.app.state.app_state
    return [e.to_dict() for e in state.registry.list_evals(model_id, task_name)]


@router.get("/failures")
def list_failures(request: Request, model_id: Optional[str] = None,
                  task_name: Optional[str] = None, status: Optional[str] = None):
    state = request.app.state.app_state
    status_enum = FailureStatus(status) if status else None
    return [c.to_dict() for c in state.registry.list_failures(model_id, task_name, status_enum)]


@router.post("/failures")
def create_failure(request: Request, req: FailureCreateRequest):
    """创建失败 Case（自动接入飞轮池）"""
    state = request.app.state.app_state
    case = FailureCase(
        case_id=f"case_manual_{len(state.registry.list_failures()) + 1:04d}",
        task_name=req.task_name,
        model_id=req.model_id,
        episode_id=req.episode_id,
        robot_id=req.robot_id,
        failure_type=req.failure_type,
        description=req.description,
        priority=req.priority,
        status=FailureStatus.OPEN,
    )
    state.registry.register_failure(case)
    return case.to_dict()


@router.get("/lineage/{model_id}")
def lineage(request: Request, model_id: str):
    """模型完整血缘（数据集 -> 训练任务 -> 模型 -> 评测 -> 失败 Case）"""
    state = request.app.state.app_state
    return state.registry.trace_lineage(model_id)


@router.get("/low-success")
def low_success(request: Request, model_id: Optional[str] = None, threshold: float = 0.5):
    """低成功率任务识别（数据飞轮输入）"""
    state = request.app.state.app_state
    if not model_id:
        model_id = state.latest_model_id()
    return {
        "model_id": model_id,
        "tasks": state.registry.low_success_tasks(model_id, threshold=threshold),
        "detail": state.registry.aggregate_success_rate_by_task(model_id),
    }
