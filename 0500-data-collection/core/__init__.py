"""核心层: schema / recorder / video / utils / verify"""
from .schema import Frame, build_step_dict, validate_frame, ACTION_NAMES, STATE_NAMES
from .recorder import EpisodeRecorder, EpisodeRecord
from .video import FrameWriter, save_video, read_frames
from .utils import set_seed, ensure_rgb, normalize_action, safe_json_dump, list_episodes, find_episode_dir
from .verify import verify_dataset, compute_stats, DatasetReport

__all__ = [
    "Frame", "build_step_dict", "validate_frame", "ACTION_NAMES", "STATE_NAMES",
    "EpisodeRecorder", "EpisodeRecord",
    "FrameWriter", "save_video", "read_frames",
    "set_seed", "ensure_rgb", "normalize_action", "safe_json_dump",
    "list_episodes", "find_episode_dir",
    "verify_dataset", "compute_stats", "DatasetReport",
]