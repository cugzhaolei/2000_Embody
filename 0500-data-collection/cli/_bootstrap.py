"""
命令行引导（跨平台 / 无 -m 执行兼容）
====================================
原因: "0500-data-collection" 目录名以数字开头，不是合法的 Python
包名，无法使用 `python -m 0500-data-collection...`。本模块把该目录
注册为合法别名 `embodied_data` 注入 sys.modules，随后各 CLI 脚本
即可用绝对导入 `from embodied_data.core...` 调用内部子模块。

用法（任一入口均可）:
  python 0500-data-collection/cli/collect.py ...
  python 0500-data-collection/run.py collect ...
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

PACKAGE_ALIAS = "embodied_data"
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent


def _fix_stdout_encoding():
    """Windows GBK 控制台打印中文乱码时，改回 UTF-8 输出。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


_fix_stdout_encoding()


def register_package() -> str:
    """把 0500-data-collection 目录注册为 sys.modules[embodied_data]。

    Returns:
        别名包名。
    """
    if PACKAGE_ALIAS in sys.modules:
        return PACKAGE_ALIAS

    init_path = PACKAGE_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        PACKAGE_ALIAS, str(init_path),
        submodule_search_locations=[str(PACKAGE_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_ALIAS] = module
    if spec.loader:
        spec.loader.exec_module(module)
    return PACKAGE_ALIAS


def import_sub(relative_name: str):
    """按别名导入子模块，解引用相对路径写法。

    Args:
        relative_name: 如 "core.recorder" -> embodied_data.core.recorder
    """
    register_package()
    return importlib.import_module(f"{PACKAGE_ALIAS}.{relative_name}")


def run_cli(module_name: str):
    """加载并执行 cli 模块的 main()。

    用法: run_cli("collect")
    """
    register_package()
    mod = importlib.import_module(f"{PACKAGE_ALIAS}.cli.{module_name}")
    mod.main()