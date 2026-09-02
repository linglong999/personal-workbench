"""Skill 注册表：主管唯一调度入口（主管→注册表→Skill，单向依赖）。

M1-B1 注册 3 个迁移 Skill；M1-B2 补齐 decision/action 成 5。
"""

from workbench.ai.skills.base import Skill
from workbench.ai.skills.classify import ClassifySkill
from workbench.ai.skills.recall import RecallSkill
from workbench.ai.skills.review import ReviewSkill

REGISTRY: dict[str, type[Skill]] = {
    "classify": ClassifySkill,
    "review": ReviewSkill,
    "recall": RecallSkill,
}


def get_skill(name: str) -> Skill:
    """按名取 Skill 实例；未知名抛 KeyError（主管路由错误的显式信号）。"""
    try:
        return REGISTRY[name]()
    except KeyError:
        raise KeyError(f"unknown skill: {name}") from None
