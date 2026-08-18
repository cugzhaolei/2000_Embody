# rosagent.modules — 模块注册表
from __future__ import annotations

from . import (action_demo, bag_record, common, launch_run, params_demo,
               pubsub, service_client, turtlesim)
from .base import BaseModule

# 模块注册表：id → 类。新增模块时 import + 注册即可，场景脚本无需改引擎。
MODULES: dict[str, type[BaseModule]] = {
    common.CleanModule.id: common.CleanModule,
    common.TopicViewModule.id: common.TopicViewModule,
    common.RobotStateModule.id: common.RobotStateModule,
    turtlesim.TurtlesimModule.id: turtlesim.TurtlesimModule,
    pubsub.PubSubModule.id: pubsub.PubSubModule,
    service_client.ServiceClientModule.id: service_client.ServiceClientModule,
    action_demo.ActionDemoModule.id: action_demo.ActionDemoModule,
    params_demo.ParamsDemoModule.id: params_demo.ParamsDemoModule,
    bag_record.BagRecordModule.id: bag_record.BagRecordModule,
    launch_run.LaunchRunModule.id: launch_run.LaunchRunModule,
}


def get_module_class(module_id: str) -> type[BaseModule]:
    if module_id not in MODULES:
        raise KeyError(
            f"未知模块 {module_id!r}。可用模块: {', '.join(sorted(MODULES))}")
    return MODULES[module_id]


def list_modules() -> str:
    lines = []
    for mid, cls in sorted(MODULES.items()):
        lines.append(f"{mid:<14} {cls.desc}")
        lines.append(cls.param_docs())
    return "\n".join(lines)