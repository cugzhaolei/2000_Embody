"""pytest 引导：把 "0500-data-infra" 目录注册为合法包别名 embodied_infra。

项目目录以数字开头不是合法 Python 包名，与 smoke_new_modules.py / run_web.py
使用同一别名技巧：将项目根 __init__.py 以 embodied_infra 名称加载进 sys.modules，
使 tests 中的 `from embodied_infra...` 导入可用。
"""

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


_register_package()
