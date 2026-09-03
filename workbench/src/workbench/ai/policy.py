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
    """M1 确定性路由 + M2 双链管线 + M3 决策带历史参照：分类 → 按标签走价值环节 → recall 收尾。

    M2-B1 起 interrupt 全部由 policy 发出（orchestrator 纯执行器，policy 是唯一
    "想"的场所）：decision 低置信 → judgement；action 草稿 → recall 候选 → link
    分流 → confirm（payload 携带 links/pending_review）。
    M3-B1：决策流前置 recall(history) 召回历史决策参照注入 decision（R1 只消费）。
    recall 三档用途以 args.purpose 区分（history/candidates/finish），互不串档。
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
            rec = self._latest_recall(run, "history")
            if rec is None:
                return RunSkill(
                    "recall",
                    {"task": run.input, "top_k": 3, "purpose": "history"},
                    thought="决策输入 → 召回历史决策参照",
                )
            return RunSkill(
                "decision",
                {"text": run.input, "history": rec.result.get("results", [])},
                thought="参照就绪 → 带历史经验的结构化分析",
            )
        if d.result.get("needs_judgement"):
            res = run.resolution("judgement")
            if res is None:
                return Interrupt(
                    "judgement",
                    {"analysis": d.result},
                    thought="决策低置信 → 请用户拍板",
                )
            if res.get("action") != "approve":
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
            return self._confirm_pipeline(run, out, kind, label)
        return self._finish(run, {"label": label, "written": True, "path": out.get("path", "")})

    def _confirm_pipeline(self, run: RunView, out: dict, kind: str, label: str) -> Instruction:
        """M2 双链管线：action 草稿 → recall 候选 → link 分流 → confirm → 写入。"""
        res = run.resolution("confirm")
        if res is None:
            rec = self._latest_recall(run, "candidates")
            if rec is None:
                query = f"{out.get('title', '')}\n{out.get('content', '')}"
                return RunSkill(
                    "recall",
                    {"task": query, "top_k": 20, "purpose": "candidates"},
                    thought="草稿就绪 → 召回关联候选",
                )
            link = run.latest_step("link")
            if link is None:
                return RunSkill(
                    "link",
                    {
                        "title": out.get("title", ""),
                        "content": out.get("content", ""),
                        "candidates": rec.result.get("results", []),
                    },
                    thought="候选就绪 → 三档分流定双链",
                )
            return Interrupt(
                "confirm",
                {
                    "preview": out,
                    "links": link.result.get("links", []),
                    "pending_review": link.result.get("pending_review", []),
                },
                thought="写库副作用 → 等待用户确认（附建议双链）",
            )
        if res.get("action") == "approve":
            link = run.latest_step("link")
            links = link.result.get("links", []) if link else []
            return RunSkill(
                "action",
                {"kind": kind, "text": run.input, "confirmed": True, "links": links},
                thought="已确认 → 写入 Vault（含双链）",
            )
        return self._finish(run, {"label": label, "written": False, "user_rejected": True})

    def _review_flow(self, run: RunView) -> Instruction:
        r = run.latest_step("review")
        if r is None:
            return RunSkill("review", {}, thought="复盘类输入 → 扫描决策闭环")
        return self._finish(run, {"label": "复盘", "missing": r.result.get("missing", [])})

    def _finish(self, run: RunView, output: dict) -> Instruction:
        """收尾前先 recall：把相关历史经验附在最终输出（"带着经验回来"）。"""
        rec = self._latest_recall(run, "finish")
        if rec is None:
            return RunSkill(
                "recall",
                {"task": run.input, "top_k": 3, "purpose": "finish"},
                thought="收尾：召回相关历史经验",
            )
        return Finish(
            {**output, "related": rec.result.get("results", [])}, thought="完成"
        )

    @staticmethod
    def _latest_recall(run: RunView, purpose: str) -> Step | None:
        """按用途找 recall（M3-B1 起三档）：history=决策参照 / candidates=双链候选 /
        finish=收尾——purpose 键互不串档；缺省视作 candidates（兼容无标志旧步）。"""
        for s in reversed(run.steps):
            if s.skill == "recall" and s.args.get("purpose", "candidates") == purpose:
                return s
        return None
