"""路由策略：主管的"想"——从运行轨迹决定下一步指令（M1-B3）。

主管（orchestrator.py）是执行语义，策略是路由决策。策略为纯函数式：只读 RunView
（输入 + 已执行步骤 + 中断及其裁决），返回一条指令，自身无状态。
M1 为确定性规则路由（ReAct 框架先立、Thought 为规则；LLM 自由规划留 M5+）。
"""

from dataclasses import dataclass
from typing import Protocol

KNOWN_LABELS = {"输入", "决策", "实践", "复盘", "创造"}


@dataclass
class Step:
    skill: str
    args: dict
    result: dict
    confidence: float = 1.0


@dataclass
class InterruptRecord:
    kind: str  # confirm / disambiguate / judgement
    payload: dict
    resolution: dict | None = None  # resume 后填入 {"action": "approve"/"reject"/...}


@dataclass
class RunView:
    """策略可见的运行轨迹（只读快照）。"""

    input: str
    steps: list[Step]
    interrupts: list[InterruptRecord]

    def latest_step(self, skill: str) -> Step | None:
        for s in reversed(self.steps):
            if s.skill == skill:
                return s
        return None

    def resolution(self, kind: str) -> dict | None:
        """最近一次该类中断的裁决（未裁决返回 None）。"""
        for it in reversed(self.interrupts):
            if it.kind == kind:
                return it.resolution
        return None


@dataclass
class RunSkill:
    skill: str
    args: dict
    thought: str = ""


@dataclass
class Interrupt:
    kind: str
    payload: dict
    thought: str = ""


@dataclass
class Finish:
    output: dict
    thought: str = ""


Instruction = RunSkill | Interrupt | Finish


class Policy(Protocol):
    def next_instruction(self, run: RunView) -> Instruction: ...


class RulePolicy:
    """M1 确定性路由：分类 → 按标签走价值环节 → recall 收尾。

    resume 安全默认：confirm/judgement 的裁决非 approve 一律不触发写库（宁可不写，不可误写）。
    """

    def next_instruction(self, run: RunView) -> Instruction:
        c = run.latest_step("classify")
        if c is None:
            return RunSkill("classify", {"text": run.input}, thought="先分类：确定输入属于哪个价值环节")
        label = c.result.get("label", "")
        if label not in KNOWN_LABELS:
            res = run.resolution("disambiguate")
            if res is None:
                return Interrupt(
                    "disambiguate",
                    {"candidates": sorted(KNOWN_LABELS), "raw": label},
                    thought=f"分类结果「{label}」不在已知五类，请用户澄清",
                )
            label = res.get("label", "")
            if label not in KNOWN_LABELS:
                return self._finish(run, {"label": label, "note": "用户选择无效，结束"})
        if label == "决策":
            return self._decision_flow(run)
        if label == "实践":
            return self._action_flow(run, "待办", label)
        if label == "复盘":
            return self._review_flow(run)
        return self._finish(run, {"label": label, "note": "M1 仅分类打标；输入/创造的深化见 M2/M3"})

    def _decision_flow(self, run: RunView) -> Instruction:
        d = run.latest_step("decision")
        if d is None:
            return RunSkill("decision", {"text": run.input}, thought="决策类输入 → 结构化分析")
        if d.result.get("needs_judgement"):
            res = run.resolution("judgement")
            if not (res and res.get("action") == "approve"):
                return self._finish(
                    run,
                    {"label": "决策", "decision": d.result, "written": False, "user_rejected": True},
                )
        return self._action_flow(run, "决策备忘", "决策")

    def _action_flow(self, run: RunView, kind: str, label: str) -> Instruction:
        a = run.latest_step("action")
        if a is None:
            return RunSkill("action", {"kind": kind, "text": run.input}, thought=f"label={label} → 起草{kind}")
        out = a.result
        if out.get("status") == "needs_confirmation":
            res = run.resolution("confirm")
            if res and res.get("action") == "approve":
                return RunSkill(
                    "action",
                    {"kind": kind, "text": run.input, "confirmed": True},
                    thought="已确认 → 写入 Vault",
                )
            return self._finish(
                run, {"label": label, "written": False, "user_rejected": True}
            )
        return self._finish(run, {"label": label, "written": True, "path": out.get("path", "")})

    def _review_flow(self, run: RunView) -> Instruction:
        r = run.latest_step("review")
        if r is None:
            return RunSkill("review", {}, thought="复盘类输入 → 扫描决策闭环")
        return self._finish(run, {"label": "复盘", "missing": r.result.get("missing", [])})

    def _finish(self, run: RunView, output: dict) -> Instruction:
        """收尾前先 recall：把相关历史经验附在最终输出（"带着经验回来"）。"""
        rec = run.latest_step("recall")
        if rec is None:
            return RunSkill("recall", {"task": run.input, "top_k": 3}, thought="收尾：召回相关历史经验")
        return Finish(
            {**output, "related": rec.result.get("results", [])}, thought="完成"
        )
