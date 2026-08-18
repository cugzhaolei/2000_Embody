"""自动标注 API"""

from typing import List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/annotation", tags=["annotation"])


class LabelRequest(BaseModel):
    episode_id: str = "ep_demo"
    eef_pose: Optional[List[List[float]]] = None   # (T, 6) 末端位姿
    demo: Optional[str] = None                    # "good" | "bad" 演示轨迹
    success: Optional[bool] = None                # 外部给定成败


def _demo_trajectory(kind: str) -> np.ndarray:
    T = 100
    traj = np.zeros((T, 6))
    traj[:, 0] = np.linspace(0, 1.5, T)
    traj[:, 2] = np.linspace(0.3, 0.35, T)
    if kind == "bad":
        traj[50:, 0] += 0.5     # 跳变
    return traj


@router.post("/label")
def label(request: Request, req: LabelRequest):
    """标注单个 Episode（轨迹/成功标记/图像质量）"""
    from ...annotation.auto_labeler import AutoLabeler

    if req.demo:
        if req.demo not in ("good", "bad"):
            raise HTTPException(status_code=400, detail="demo 只能是 good/bad")
        traj = _demo_trajectory(req.demo)
    elif req.eef_pose is not None:
        traj = np.asarray(req.eef_pose, dtype=np.float64)
        if traj.ndim != 2 or traj.shape[1] != 6:
            raise HTTPException(status_code=400, detail="eef_pose 必须是 (T, 6) 数组")
    else:
        raise HTTPException(status_code=400, detail="需提供 eef_pose 或 demo")

    episode_data = {"eef_pose": traj}
    if req.success is not None:
        episode_data["success"] = req.success

    labeler = AutoLabeler()
    result = labeler.label_episode(episode_data, episode_id=req.episode_id)
    return result.to_dict()
