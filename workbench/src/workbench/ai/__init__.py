"""AI 模块：engine（LLM 能力）+ skills（注册表派发）+ orchestrator（主管）。

M1-B5 起 agents.py 退役：角色职责已迁移进 Skill 注册表（classify/review/recall）
与主管（decision/action 的 interrupt 接线）。
"""

from workbench.ai.engine import AIEngine

__all__ = ["AIEngine"]
