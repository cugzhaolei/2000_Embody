"""总览 Dashboard API"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(request: Request):
    """聚合全平台状态，供总览页使用"""
    state = request.app.state.app_state
    return state.snapshot()
