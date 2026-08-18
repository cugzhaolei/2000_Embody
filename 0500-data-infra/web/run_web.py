"""
Web 平台启动入口
================
用法:
  python 0500-data-infra/web/run_web.py [--host 0.0.0.0] [--port 8000]

说明: "0500-data-infra" 目录名以数字开头不是合法 Python 包名，这里先将其
注册为别名 embodied_infra，再导入 web 应用。
"""

import argparse
import importlib.util
import pathlib
import sys

PACKAGE_ALIAS = "embodied_infra"
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent


def _register_package() -> str:
    if PACKAGE_ALIAS in sys.modules:
        return PACKAGE_ALIAS
    spec = importlib.util.spec_from_file_location(
        PACKAGE_ALIAS, str(PACKAGE_DIR / "__init__.py"),
        submodule_search_locations=[str(PACKAGE_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_ALIAS] = module
    spec.loader.exec_module(module)
    return PACKAGE_ALIAS


def main():
    parser = argparse.ArgumentParser(description="Embodied Data Infra Web Platform")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    _register_package()
    import uvicorn

    uvicorn.run(
        "embodied_infra.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
