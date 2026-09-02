"""Skill 统一协议（M1-C）：主管经注册表调度，Skill 只从 ctx 拿能力。

requires_confirmation 对齐 interrupt 映射（confirm 型：写库等副作用动作）；
confidence 由 run() 按实际情况返回，主管用它判低置信升级（disambiguate/judgement）。
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from workbench.ai.engine import AIEngine
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore


@dataclass
class SkillContext:
    """Skill 的能力注入。Skill 不依赖主管，只从这里拿依赖。"""

    engine: AIEngine
    vault: VaultStore
    vector: VectorStore


@dataclass
class SkillResult:
    """Skill 执行结果。output 为 skill 自有契约；confidence 供主管判 interrupt。"""

    output: dict
    confidence: float = 1.0


@runtime_checkable
class Skill(Protocol):
    name: str
    description: str
    requires_confirmation: bool

    def run(self, ctx: SkillContext, args: dict) -> SkillResult: ...
