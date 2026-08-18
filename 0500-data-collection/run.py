"""
统一入口（可选，便于统一调用）
==============================
python 0500-data-collection/run.py collect -s dummy -n 3
python 0500-data-collection/run.py verify -d ./data/episodes
python 0500-data-collection/run.py stats -d ./data/episodes
python 0500-data-collection/run.py replay -d ./data/episodes -e 0
python 0500-data-collection/run.py visualize -d ./data/episodes
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))  # 仓库根目录（可供 0200-vla-imitation/envs 复用）


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    allowed = {"collect", "verify", "stats", "replay", "visualize"}
    if command not in allowed:
        sys.stderr.write(f"未知命令: {command} (可选: {', '.join(sorted(allowed))})\n")
        sys.exit(1)

    target = ROOT / "cli" / f"{command}.py"
    spec = importlib.util.spec_from_file_location(f"embodied_data.cli.{command}", str(target))
    mod = importlib.util.module_from_spec(spec)
    sys.argv = [str(target)] + sys.argv[2:]
    if spec.loader:
        spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        raise SystemExit(mod.main())


if __name__ == "__main__":
    main()