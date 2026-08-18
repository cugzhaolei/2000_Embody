"""Ego 长视频处理 API"""

from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..demo_data import generate_ego_scenario

router = APIRouter(prefix="/api/ego", tags=["ego"])


class EgoProcessRequest(BaseModel):
    """自定义序列处理请求"""
    motion: Optional[List[float]] = None
    timestamps: Optional[List[float]] = None
    hand_openness: Optional[List[float]] = None
    params: Dict[str, Any] = Field(default_factory=dict)  # segmenter 参数覆盖


class EgoDemoRequest(BaseModel):
    """合成场景请求"""
    duration_sec: float = 120.0
    fps: float = 30.0
    operation_windows: Optional[List[Dict[str, float]]] = None
    motion_amplitude: float = 0.08
    params: Dict[str, Any] = Field(default_factory=dict)


def _run_pipeline(motion, timestamps, hand_openness, params) -> Dict[str, Any]:
    from ...ego.video_segmenter import EgoVideoSegmenter
    from ...ego.action_phase import ActionPhaseRecognizer
    from ...ego.abnormal_filter import EgoAbnormalFilter
    from ...ego.sample_generator import EgoSampleGenerator

    motion_arr = np.asarray(motion, dtype=np.float64)
    ts_arr = np.asarray(timestamps, dtype=np.float64) if timestamps else None
    open_arr = (
        np.asarray(hand_openness, dtype=np.float64)
        if hand_openness is not None else None
    )

    if motion_arr.ndim != 1 or len(motion_arr) < 10:
        raise HTTPException(status_code=400, detail="motion 必须是长度 >= 10 的一维数组")

    if ts_arr is not None and len(ts_arr) != len(motion_arr):
        raise HTTPException(status_code=400, detail="timestamps 长度必须与 motion 一致")
    if open_arr is not None and len(open_arr) != len(motion_arr):
        raise HTTPException(status_code=400, detail="hand_openness 长度必须与 motion 一致")

    seg_params = dict(params)
    fps = 1.0 / (ts_arr[1] - ts_arr[0]) if ts_arr is not None and len(ts_arr) > 1 and ts_arr[1] > ts_arr[0] else 30.0

    segmenter = EgoVideoSegmenter(**{
        k: v for k, v in seg_params.items()
        if k in ("motion_threshold", "low_motion_ratio", "min_active_sec",
                 "min_idle_sec", "pad_sec", "default_fps", "min_segment_len")
    })
    segments = segmenter.segment_by_motion(motion_arr, ts_arr, hand_presence=None)

    recognizer = ActionPhaseRecognizer()
    spans = recognizer.recognize(motion_arr, open_arr, ts_arr)

    filt = EgoAbnormalFilter()
    kept, filter_results = filt.filter_segments(segments, motion=motion_arr)

    gen = EgoSampleGenerator()
    samples = gen.generate(
        segments,
        source_video="demo_video.mp4",
        success_labels={s.segment_id: s in kept for s in segments},
        phase_spans=spans,
        quality_scores={r.segment_id: _verdict_score(r) for r in filter_results},
    )

    # 运动量降采样（供前端图表）
    step = max(1, len(motion_arr) // 600)
    sampled_idx = np.arange(0, len(motion_arr), step)

    return {
        "fps": fps,
        "n_frames": len(motion_arr),
        "segments": [s.to_dict() for s in segments],
        "kept_ids": [s.segment_id for s in kept],
        "filter_results": [r.to_dict() for r in filter_results],
        "phase_spans": [s.to_dict() for s in spans],
        "samples_count": len(samples),
        "motion": {
            "t": [float(ts_arr[i]) if ts_arr is not None else float(i / fps) for i in sampled_idx],
            "v": [float(motion_arr[i]) for i in sampled_idx],
            "step": step,
        },
    }


def _verdict_score(r) -> float:
    return 0.2 if r.verdict.value == "discard" else 1.0


@router.post("/demo")
def process_demo(req: EgoDemoRequest):
    """合成一段 Ego 场景并执行完整处理流水线"""
    scenario = generate_ego_scenario(
        duration_sec=req.duration_sec,
        fps=req.fps,
        operation_windows=req.operation_windows,
        motion_amplitude=req.motion_amplitude,
    )
    result = _run_pipeline(
        scenario["motion"], scenario["timestamps"], scenario["hand_openness"], req.params
    )
    result["scenario"] = {
        "duration_sec": req.duration_sec,
        "operation_windows": scenario["operation_windows"],
    }
    return result


@router.post("/process")
def process_custom(req: EgoProcessRequest):
    """处理用户上传的运动/开合度序列"""
    if req.motion is None:
        raise HTTPException(status_code=400, detail="motion 必填（或用 /demo 合成场景）")
    return _run_pipeline(req.motion, req.timestamps, req.hand_openness, req.params)
