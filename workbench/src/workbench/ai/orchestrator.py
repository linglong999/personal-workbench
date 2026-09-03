"""ReAct 主管 Orchestrator：显式状态图 + 循环节点内逻辑（M1-B3）。

状态图（计划 M1-B）：IDLE→INGEST→ACTING→(interrupt)WAITING_HUMAN→(resume)ACTING→DONE；
任一步失败/超时→ERROR；放弃/等待超时→DONE。每跳产生 domain event（修正 A：事件是执行
语义，trace 是观测层——B4 落 TraceStore）。
守护（计划 M1-B）：max_steps / budget_seconds / human_wait_timeout（超时按放弃→DONE）。
主管级 interrupt 接线：action needs_confirmation→confirm；decision needs_judgement→judgement。
"""

import itertools
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from workbench.ai.policy import (
    Finish,
    Interrupt,
    InterruptRecord,
    Policy,
    RulePolicy,
    RunSkill,
    RunView,
    Step,
)
from workbench.ai.skills.base import SkillContext
from workbench.ai.skills.registry import get_skill
from workbench.ai.trace import TraceStore


class OrchState(str, Enum):
    IDLE = "IDLE"
    INGEST = "INGEST"
    ACTING = "ACTING"
    WAITING_HUMAN = "WAITING_HUMAN"
    DONE = "DONE"
    ERROR = "ERROR"


@dataclass
class Guards:
    """执行守护（计划 M1-B 基准：普通任务 max_steps 50–150）。"""

    max_steps: int = 50
    budget_seconds: float | None = None
    human_wait_timeout: float | None = None  # None=不限；超时按放弃→DONE


@dataclass
class DomainEvent:
    """每跳必产的 domain event（观测层的原料，B4 落 TraceStore）。"""

    seq: int
    ts: float
    state_from: str
    state_to: str
    event: str
    thought: str = ""
    tool: str = ""
    args: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)
    confidence: float | None = None
    interrupt_kind: str = ""
    payload: dict = field(default_factory=dict)
    human_decision: dict | None = None
    reason: str = ""


@dataclass
class TurnResult:
    status: str  # done / waiting_human / error
    state: OrchState
    output: dict
    interrupt: dict | None = None  # {"kind": ..., "payload": ...}
    events: list[DomainEvent] = field(default_factory=list)


def _new_run_id() -> str:
    """时间戳-短哈希：文件名即排序键（TraceStore 一 run 一文件）。"""
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


class Orchestrator:
    """单回合有状态：run() 起、resume() 续；DONE/ERROR 后可 run() 重开新回合（轨迹清零）。"""

    def __init__(
        self,
        ctx: SkillContext,
        policy: Policy | None = None,
        guards: Guards | None = None,
        clock: Callable[[], float] = time.monotonic,
        trace: TraceStore | None = None,
    ):
        self.ctx = ctx
        self.policy = policy or RulePolicy()
        self.guards = guards or Guards()
        self.clock = clock
        self.trace = trace
        self.state = OrchState.IDLE
        self.input = ""
        self.run_id = ""
        self.steps: list[Step] = []
        self.interrupts: list[InterruptRecord] = []
        self.events: list[DomainEvent] = []
        self._seq = itertools.count(1)
        self._started = 0.0
        self._deadline: float | None = None

    def run(self, text: str) -> TurnResult:
        if self.state not in (OrchState.IDLE, OrchState.DONE, OrchState.ERROR):
            raise RuntimeError(f"run() 非法状态: {self.state}")
        self._reset_turn()
        self.run_id = _new_run_id()
        self.input = (text or "").strip()
        self._emit(self.state, OrchState.INGEST, "ingest", payload={"text": self.input})
        if not self.input:
            return self._error(OrchState.INGEST, "empty_input")
        self._started = self.clock()
        self._emit(OrchState.INGEST, OrchState.ACTING, "act")
        return self._loop()

    def resume(self, decision: dict) -> TurnResult:
        if self.state != OrchState.WAITING_HUMAN:
            raise RuntimeError(f"resume() 非法状态: {self.state}")
        if self._deadline is not None and self.clock() > self._deadline:
            self._emit(
                OrchState.WAITING_HUMAN,
                OrchState.DONE,
                "timeout",
                reason="human_wait_timeout",
            )
            return TurnResult(
                "done",
                self.state,
                {"abandoned": True, "reason": "human_wait_timeout"},
                None,
                self.events,
            )
        self.interrupts[-1].resolution = dict(decision)
        if decision.get("action") == "abandon":
            self._emit(
                OrchState.WAITING_HUMAN,
                OrchState.DONE,
                "abandon",
                human_decision=dict(decision),
            )
            return TurnResult("done", self.state, {"abandoned": True}, None, self.events)
        self._emit(
            OrchState.WAITING_HUMAN,
            OrchState.ACTING,
            "resume",
            human_decision=dict(decision),
        )
        # budget 只算机器时间：人机等待不计入预算，resume 重置计时起点
        self._started = self.clock()
        return self._loop()

    # ── 内部：主循环与状态转移 ──

    def _loop(self) -> TurnResult:
        while True:
            if len(self.steps) >= self.guards.max_steps:
                return self._error(OrchState.ACTING, f"max_steps({self.guards.max_steps}) exceeded")
            if (
                self.guards.budget_seconds is not None
                and (self.clock() - self._started) > self.guards.budget_seconds
            ):
                return self._error(OrchState.ACTING, "budget exceeded")
            try:
                instr = self.policy.next_instruction(self._view())
            except Exception as e:
                return self._error(OrchState.ACTING, f"policy: {e}")
            if isinstance(instr, Finish):
                self._emit(
                    OrchState.ACTING,
                    OrchState.DONE,
                    "finish",
                    thought=instr.thought,
                    result=instr.output,
                )
                return TurnResult("done", self.state, instr.output, None, self.events)
            if isinstance(instr, Interrupt):
                return self._wait(instr.kind, instr.payload, instr.thought)
            assert isinstance(instr, RunSkill)
            try:
                skill = get_skill(instr.skill)
                sr = skill.run(self.ctx, instr.args)
            except Exception as e:
                return self._error(OrchState.ACTING, f"skill {instr.skill}: {e}")
            self.steps.append(Step(instr.skill, instr.args, sr.output, sr.confidence))
            self._emit(
                OrchState.ACTING,
                OrchState.ACTING,
                "step",
                thought=instr.thought,
                tool=instr.skill,
                args=instr.args,
                result=sr.output,
                confidence=sr.confidence,
            )
            # 主管级 interrupt 接线（读 Skill 标志/输出，B2 契约的另一半）
            if instr.skill == "action" and sr.output.get("status") == "needs_confirmation":
                return self._wait(
                    "confirm",
                    {"preview": sr.output, "confidence": sr.confidence},
                    "写库副作用 → 等待用户确认",
                )
            if instr.skill == "decision" and sr.output.get("needs_judgement"):
                return self._wait(
                    "judgement",
                    {"analysis": sr.output},
                    "决策低置信 → 请用户拍板",
                )

    def _wait(self, kind: str, payload: dict, thought: str = "") -> TurnResult:
        self.interrupts.append(InterruptRecord(kind, payload))
        if self.guards.human_wait_timeout is not None:
            self._deadline = self.clock() + self.guards.human_wait_timeout
        self._emit(
            OrchState.ACTING,
            OrchState.WAITING_HUMAN,
            "interrupt",
            thought=thought,
            interrupt_kind=kind,
            payload=payload,
        )
        return TurnResult(
            "waiting_human", self.state, payload, {"kind": kind, "payload": payload}, self.events
        )

    def _error(self, frm: OrchState, reason: str) -> TurnResult:
        self._emit(frm, OrchState.ERROR, "error", reason=reason)
        return TurnResult("error", self.state, {"error": reason}, None, self.events)

    def _emit(self, frm: OrchState, to: OrchState, event: str, **fields: Any) -> None:
        self.events.append(
            DomainEvent(
                seq=next(self._seq),
                ts=self.clock(),
                state_from=frm.value,
                state_to=to.value,
                event=event,
                **fields,
            )
        )
        self.state = to
        # 观测点快照：进入等待/终态时落盘（修正 A：trace 是观测层，写失败不杀任务）
        if to in (OrchState.WAITING_HUMAN, OrchState.DONE, OrchState.ERROR):
            self._save_trace()

    def _save_trace(self) -> None:
        if self.trace is None:
            return
        try:
            self.trace.save(
                {"run_id": self.run_id, "input": self.input, "status": self.state.value.lower()},
                [asdict(e) for e in self.events],
            )
        except Exception:
            pass  # 修正 A：观测层失败静默——宁可不记，不可误杀任务

    def _view(self) -> RunView:
        return RunView(self.input, list(self.steps), list(self.interrupts))

    def _reset_turn(self) -> None:
        self.steps = []
        self.interrupts = []
        self.events = []
        self._seq = itertools.count(1)
        self._deadline = None
