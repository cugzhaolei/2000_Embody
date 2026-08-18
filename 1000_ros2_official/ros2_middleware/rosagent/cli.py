# rosagent.cli — 命令行入口
"""用法：
  python3 -m rosagent detect
  python3 -m rosagent env
  python3 -m rosagent check [--pkg turtlesim,urdf-tutorial]
  python3 -m rosagent module-list
  python3 -m rosagent run scenarios/xxx.json [--watch 30]
  python3 -m rosagent clean
"""
from __future__ import annotations

import argparse
import sys

from . import registry as _reg
from .checks import Checks
from .detector import detect
from .env import EnvironmentManager
from .modules import list_modules
from .runner import ScenarioRunner
from .runtime import RuntimeManager


def build() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rosagent", description="ROS 2 中间层 Agent")
    p.add_argument("-v", "--version", action="version", version="rosagent 0.1.0")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("detect", help="检测 OS / ROS 版本 / 工作空间")
    sub.add_parser("env", help="显示适配后的环境与提示")
    sub.add_parser("clean", help="清理遗留进程与内存")
    sub.add_parser("module-list", help="列出可组合的模块与参数")

    ck = sub.add_parser("check", help="运行检查")
    ck.add_argument("--pkg", default="", help="逗号分隔的逻辑包名，如 turtlesim,tf2-tools")

    rn = sub.add_parser("run", help="运行一个场景脚本 (JSON)")
    rn.add_argument("scenario", help="场景文件路径")
    rn.add_argument("--watch", type=float, default=0.0, help="观察秒数（0 不观察）")
    rn.add_argument("--keep", action="store_true", help="结束后不自动 teardown")
    return p


def _envman() -> tuple:
    reg = _reg.default_registry()
    env = detect(reg)
    return EnvironmentManager(env, reg), RuntimeManager(EnvironmentManager(env, reg))


def main(argv=None) -> int:
    args = build().parse_args(argv)
    reg = _reg.default_registry()

    if not args.cmd:
        build().print_help()
        return 0

    if args.cmd == "detect":
        env = detect(reg)
        print(env.summary())
        return 0

    envman, rt = _envman()
    env = envman.env

    if args.cmd == "env":
        print(envman.describe())
        print("source 前缀:", envman.source_prefix())
        if env.distro:
            print("示例 apt 包名:", envman.apt_pkg("turtlesim"))
            print("Python 需求  :", envman.python_version_req())
        return 0

    if args.cmd == "clean":
        print(rt.cleanup())
        return 0

    if args.cmd == "module-list":
        print(list_modules())
        return 0

    if args.cmd == "check":
        chk = Checks(envman, rt)
        chk.environment()
        logicals = [s.strip() for s in args.pkg.split(",") if s.strip()]
        if logicals:
            chk.apt_pkgs(logicals)
        print(chk.reporter.render())
        return 0 if chk.reporter.passed() else 1

    if args.cmd == "run":
        runner = ScenarioRunner(envman, reg)
        scenario = runner.load(args.scenario)
        result = runner.run(scenario, watch=args.watch, fail_fast=True)
        print(result.render())
        return 0 if result.ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())