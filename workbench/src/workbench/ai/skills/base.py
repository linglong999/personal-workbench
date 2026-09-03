"""Skill 统一协议（M1-C）：主管经注册表调度，Skill 只从 ctx 拿能力。

requires_confirmation 对齐 interrupt 映射（confirm 型：写库等副作用动作）；
confidence 由 run() 按实际情况返回，主管用它判低置信升级（disambiguate/judgement）。
engine/vector 是结构协议（EngineLike/VectorLike）：真实现与 eval/测试的脚本化实现
均可注入——Skill 依赖能力接口，不绑定具体类。
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from workbench.knowledge.vault import VaultStore


class EngineLike(Protocol):
    """Skill 依赖的引擎能力（AIEngine 与 CaseEngine 均结构满足）。"""

    def classify(self, text: str) -> str: ...

    def analyze_decision(self, text: str) -> dict: ...

    def draft_note(self, kind: str, text: str) -> dict: ...

    def check_closed_loop(self, decisions: list[str]) -> list[str]: ...


class VectorLike(Protocol):
    def search(self, query: str, top_k: int) -> list[dict]: ...


@dataclass
class SkillContext:
    """Skill 的能力注入。Skill 不依赖主管，只从这里拿依赖。"""

    engine: EngineLike
    vault: VaultStore
    vector: VectorLike


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
