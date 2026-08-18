"""
FastAPI 应用工厂
================
注册全部 API 路由、CORS 与静态前端页面。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .demo_data import seed
from .routers import annotation, dashboard, ego, flywheel, tracking
from .state import AppState

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Embodied Data Infra Platform",
        description="具身数据基础设施 Web 平台：Ego 长视频处理 / 自动标注 / "
                    "训练评估关联管理 / 数据飞轮",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 共享状态 + 演示种子
    app.state.app_state = AppState()
    seed(app.state.app_state)

    # API 路由
    app.include_router(dashboard.router)
    app.include_router(ego.router)
    app.include_router(annotation.router)
    app.include_router(tracking.router)
    app.include_router(flywheel.router)

    # 静态前端（在 API 路由之后挂载，优先匹配 API）
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
