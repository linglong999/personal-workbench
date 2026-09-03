"""Skill 注册表：主管唯一调度入口（主管→注册表→Skill，单向依赖）。

M1-B2 补齐 5 个：classify/review/recall（迁移）+ decision/action（新写）。
M2-B1 新增 link（写卡自动双链的三档分流），注册表满 6。
"""

from workbench.ai.skills.action import ActionSkill
from workbench.ai.skills.base import Skill
from workbench.ai.skills.classify import ClassifySkill
from workbench.ai.skills.decision import DecisionSkill
from workbench.ai.skills.link import LinkSkill
from workbench.ai.skills.recall import RecallSkill
from workbench.ai.skills.review import ReviewSkill

REGISTRY: dict[str, type[Skill]] = {
    "classify": ClassifySkill,
    "decision": DecisionSkill,
    "action": ActionSkill,
    "review": ReviewSkill,
    "recall": RecallSkill,
    "link": LinkSkill,
}


def get_skill(name: str) -> Skill:
    """按名取 Skill 实例；未知名抛 KeyError（主管路由错误的显式信号）。"""
    try:
        return REGISTRY[name]()
    except KeyError:
        raise KeyError(f"unknown skill: {name}") from None
