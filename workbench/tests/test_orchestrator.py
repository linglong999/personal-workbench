"""M1-B3 ReAct 主管测试：六状态机 + 三类 interrupt + resume + 守护 + domain event 链。

策略为确定性规则路由（RulePolicy），引擎/向量全部脚本化；Vault 用真 VaultStore（tmp_path
落盘）——B2 教训：写路径必须测真契约。事件链断言对齐修正 A（每跳必产 domain event）。
"""

import pytest

from workbench.ai.orchestrator import Guards, Orchestrator, OrchState
from workbench.ai.policy import RunSkill
from workbench.ai.skills.base import SkillContext
from workbench.knowledge.vault import VaultStore

HIGH_CONF = {
    "question": "选A还是B",
    "dimensions": ["成本", "速度"],
    "options": [{"name": "A", "pros": "快", "cons": "糙"}],
    "clarify": [],
    "lean": "倾向A",
    "confidence": 0.85,
}
LOW_CONF = {
    "question": "选A还是B",
    "dimensions": [],
    "options": [],
    "clarify": ["预算是多少？"],
    "lean": "",
    "confidence": 0.3,
}
MEMO_DRAFT = {"title": "选A方案", "content": "## 背景\n…\n## 决定\n选A\n## 关联问题\n1. 成本可控？"}
TODO_DRAFT = {"title": "联系供应商", "content": "## 下一步\n询价\n## 次日跟进\n明早10点"}


class ScriptedEngine:
    def __init__(self, label="决策", analysis=None, draft=None, judge=None):
        self.label = label
        self.analysis = analysis if analysis is not None else HIGH_CONF
        self.draft = draft if draft is not None else MEMO_DRAFT
        self.judge = judge if judge is not None else {"link_to": True, "confidence": 0.8}
        self.judge_calls: list[str] = []

    def classify(self, text):
        return self.label

    def analyze_decision(self, text):
        return self.analysis

    def draft_note(self, kind, text):
        return self.draft

    def judge_link(self, title, content, candidate):
        self.judge_calls.append(candidate.get("title", ""))
        return dict(self.judge)

    def check_closed_loop(self, decisions):
        return ["某决策 缺少关联问题"]


class FakeVector:
    """候选池可配置（M2：link 分流测试），默认命中 auto 档。"""

    def __init__(self, results=None):
        self.results = (
            results if results is not None else [{"id": "n1", "title": "相关经验", "score": 0.9}]
        )

    def search(self, query, top_k):
        return [dict(r) for r in self.results[:top_k]]

    def add(self, doc_id, title, content, path=""):
        return None  # action 确认写入的索引同步（B5 契约）：主管测试不关注索引细节


class FakeClock:
    """手动假钟：默认不前进，测试显式 advance。"""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, d):
        self.t += d


class TickClock:
    """自动前进假钟：每次读数 +step（budget 守护测试用）。"""

    def __init__(self, step):
        self.t = 0.0
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


def make_orch(tmp_path, engine=None, guards=None, clock=None, policy=None, vector=None):
    ctx = SkillContext(
        engine=engine or ScriptedEngine(),
        vault=VaultStore(str(tmp_path / "vault")),
        vector=vector or FakeVector(),
    )
    kwargs = {}
    if guards is not None:
        kwargs["guards"] = guards
    if clock is not None:
        kwargs["clock"] = clock
    if policy is not None:
        kwargs["policy"] = policy
    return Orchestrator(ctx, **kwargs)


def memo_notes(tmp_path):
    return list((tmp_path / "vault" / "决策备忘").glob("*.md"))


def todo_notes(tmp_path):
    return list((tmp_path / "vault" / "行动记录").glob("*.md"))


# ═══════════ 决策全链（happy path）═══════════


def test_decision_full_flow_with_confirm_and_recall(tmp_path):
    orch = make_orch(tmp_path)
    r1 = orch.run("选A还是B")
    assert r1.status == "waiting_human"
    assert r1.state == OrchState.WAITING_HUMAN
    assert r1.interrupt["kind"] == "confirm"
    assert r1.interrupt["payload"]["preview"]["title"] == "选A方案"  # 预览可直接展示
    # M2-B1：confirm payload 携带 link 决策（相关经验 0.9 命中 auto 档）
    assert r1.interrupt["payload"]["links"] == ["相关经验"]
    assert r1.interrupt["payload"]["pending_review"] == []

    r2 = orch.resume({"action": "approve"})
    assert r2.status == "done"
    assert r2.state == OrchState.DONE
    assert r2.output["written"] is True
    assert r2.output["path"].endswith(".md")
    assert r2.output["related"][0]["title"] == "相关经验"  # recall 收尾："带着经验回来"

    notes = memo_notes(tmp_path)
    assert len(notes) == 1  # 草稿不落盘 + 确认后写一次 = 恰好 1 张
    body = notes[0].read_text(encoding="utf-8")
    assert "关联问题" in body
    assert "[[相关经验]]" in body  # 确认后写入：auto 档双链渲染进「## 关联」

    names = [e.event for e in orch.events]
    assert names == [
        "ingest", "act", "step", "step", "step", "step", "step",
        "interrupt", "resume", "step", "step", "finish",
    ]
    tools = [e.tool for e in orch.events if e.event == "step"]
    # M2-B1 编排：action 草稿 → recall 候选 → link 决策 → confirm → action(confirmed, links) → recall 收尾
    assert tools == ["classify", "decision", "action", "recall", "link", "action", "recall"]


def test_confirm_payload_carries_pending_review(tmp_path):
    """低分候选不自动链，透出给用户裁决（<0.75 档）。"""
    vector = FakeVector(
        results=[
            {"id": "n1", "title": "相关经验", "score": 0.9},
            {"id": "n2", "title": "弱相关参考", "score": 0.6},
        ]
    )
    orch = make_orch(tmp_path, vector=vector)
    r1 = orch.run("选A还是B")
    payload = r1.interrupt["payload"]
    assert payload["links"] == ["相关经验"]  # auto 档
    assert payload["pending_review"] == [{"title": "弱相关参考", "score": 0.6}]  # 低分档
    r2 = orch.resume({"action": "approve"})
    assert r2.output["written"] is True
    body = memo_notes(tmp_path)[0].read_text(encoding="utf-8")
    assert "[[相关经验]]" in body
    assert "[[弱相关参考]]" not in body  # 低分候选未经用户裁决不落链


def test_llm_tier_candidate_linked_via_engine(tmp_path):
    """0.75~0.85 档走 LLM 判断：judge 通过则链、驳回则不链。"""
    vector = FakeVector(results=[{"id": "c1", "title": "成本考量", "score": 0.8}])
    orch = make_orch(tmp_path, vector=vector)  # ScriptedEngine.judge 默认 link_to=True
    r1 = orch.run("选A还是B")
    assert r1.interrupt["payload"]["links"] == ["成本考量"]
    orch.resume({"action": "approve"})

    vector2 = FakeVector(results=[{"id": "c1", "title": "成本考量", "score": 0.8}])
    engine = ScriptedEngine(judge={"link_to": False, "confidence": 0.7})
    orch2 = make_orch(tmp_path, engine=engine, vector=vector2)
    r = orch2.run("选A还是B")
    assert r.interrupt["payload"]["links"] == []  # LLM 驳回 → 不链
    orch2.resume({"action": "approve"})

    bodies = [n.read_text(encoding="utf-8") for n in memo_notes(tmp_path)]
    assert len(bodies) == 2
    assert any("[[成本考量]]" in b for b in bodies)  # judge 通过的那张已链
    assert any("[[成本考量]]" not in b for b in bodies)  # judge 驳回的那张未链


# ═══════════ 三类 interrupt ═══════════


def test_judgement_interrupt_approve_then_write(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(analysis=LOW_CONF))
    r1 = orch.run("选A还是B")
    assert r1.interrupt["kind"] == "judgement"  # 低置信 → 拍板
    assert r1.interrupt["payload"]["analysis"]["clarify"] == ["预算是多少？"]

    r2 = orch.resume({"action": "approve"})  # 用户拍板后继续
    assert r2.status == "waiting_human"
    assert r2.interrupt["kind"] == "confirm"

    r3 = orch.resume({"action": "approve"})
    assert r3.status == "done"
    assert r3.output["written"] is True
    assert len(memo_notes(tmp_path)) == 1


def test_judgement_reject_no_write(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(analysis=LOW_CONF))
    orch.run("选A还是B")
    r2 = orch.resume({"action": "reject"})  # 驳回：分析保留，不落库
    assert r2.status == "done"
    assert r2.output["written"] is False
    assert r2.output["user_rejected"] is True
    assert memo_notes(tmp_path) == []


def test_confirm_reject_no_write(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    r2 = orch.resume({"action": "reject"})
    assert r2.status == "done"
    assert r2.output["written"] is False
    assert memo_notes(tmp_path) == []


def test_confirm_invalid_action_is_safe_default_no_write(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    r2 = orch.resume({"action": "乱按了一个"})  # 非 approve 一律不写（安全默认）
    assert r2.status == "done"
    assert r2.output["written"] is False
    assert memo_notes(tmp_path) == []


def test_disambiguate_unknown_label_then_pick(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="乱码输出"))
    r1 = orch.run("贴入内容")
    assert r1.interrupt["kind"] == "disambiguate"
    assert r1.interrupt["payload"]["candidates"] == sorted(
        ["输入", "决策", "实践", "复盘", "创造"]
    )
    assert r1.interrupt["payload"]["raw"] == "乱码输出"

    r2 = orch.resume({"action": "pick", "label": "实践"})  # 用户选"实践"→按所选路由
    assert r2.status == "waiting_human"
    assert r2.interrupt["kind"] == "confirm"

    r3 = orch.resume({"action": "approve"})
    assert r3.status == "done"
    assert r3.output["written"] is True
    assert len(todo_notes(tmp_path)) == 1


def test_disambiguate_invalid_pick_ends_run(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="乱码输出"))
    orch.run("贴入内容")
    r2 = orch.resume({"action": "pick", "label": "还是乱选"})
    assert r2.status == "done"
    assert "note" in r2.output  # 无效选择：礼貌结束，不再循环
    assert memo_notes(tmp_path) == [] and todo_notes(tmp_path) == []


# ═══════════ abandon / 超时 ═══════════


def test_abandon_from_waiting(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    r2 = orch.resume({"action": "abandon"})  # 放弃→DONE（状态表）
    assert r2.status == "done"
    assert r2.output["abandoned"] is True
    assert memo_notes(tmp_path) == []


def test_human_wait_timeout_treated_as_abandon(tmp_path):
    clk = FakeClock()
    orch = make_orch(tmp_path, guards=Guards(human_wait_timeout=60), clock=clk)
    orch.run("选A还是B")  # interrupt 时刻 t=0，deadline=60
    clk.advance(1000)  # 用户 1000s 后才回来：超时
    r2 = orch.resume({"action": "approve"})
    assert r2.status == "done"  # 超时=放弃语义 → DONE 非 ERROR
    assert r2.output["abandoned"] is True
    assert r2.output["reason"] == "human_wait_timeout"
    assert memo_notes(tmp_path) == []


def test_human_wait_not_expired_resumes_normally(tmp_path):
    clk = FakeClock()
    orch = make_orch(tmp_path, guards=Guards(human_wait_timeout=3600), clock=clk)
    orch.run("选A还是B")
    clk.advance(10)  # 远未超时
    r2 = orch.resume({"action": "approve"})
    assert r2.status == "done"
    assert r2.output["written"] is True


# ═══════════ 守护与异常 ═══════════


class LoopPolicy:
    """永远要求再分类一次：触发 max_steps 守护。"""

    def next_instruction(self, run):
        return RunSkill("classify", {"text": "loop"})


class RaisingPolicy:
    def next_instruction(self, run):
        raise RuntimeError("policy bug")


def test_max_steps_guard(tmp_path):
    orch = make_orch(tmp_path, guards=Guards(max_steps=2), policy=LoopPolicy())
    r = orch.run("x")
    assert r.status == "error"
    assert r.state == OrchState.ERROR
    assert "max_steps" in r.output["error"]
    assert len(orch.steps) == 2


def test_budget_guard(tmp_path):
    orch = make_orch(tmp_path, guards=Guards(budget_seconds=0.1), clock=TickClock(10.0))
    r = orch.run("x")
    assert r.status == "error"
    assert "budget" in r.output["error"]
    assert orch.steps == []  # 预算耗尽在任何步骤前即拦截


def test_budget_excludes_human_wait_time(tmp_path):
    clk = FakeClock()
    orch = make_orch(tmp_path, guards=Guards(budget_seconds=60), clock=clk)
    orch.run("选A还是B")  # acting 阶段 t≈0，随后进入 WAITING_HUMAN
    clk.advance(10_000)  # 用户离开远超 budget：等待时间不应计入预算
    r2 = orch.resume({"action": "approve"})
    assert r2.status == "done"  # 不因人机等待时间误判预算耗尽
    assert r2.output["written"] is True


def test_empty_input_error(tmp_path):
    orch = make_orch(tmp_path)
    r = orch.run("   ")
    assert r.status == "error"
    assert r.output["error"] == "empty_input"


def test_skill_exception_to_error(tmp_path):
    class BoomEngine(ScriptedEngine):
        def classify(self, text):
            raise RuntimeError("LLM down")

    orch = make_orch(tmp_path, BoomEngine())
    r = orch.run("选A还是B")
    assert r.status == "error"
    assert "LLM down" in r.output["error"]


def test_policy_exception_to_error(tmp_path):
    orch = make_orch(tmp_path, policy=RaisingPolicy())
    r = orch.run("x")
    assert r.status == "error"
    assert "policy" in r.output["error"]


def test_resume_outside_waiting_raises(tmp_path):
    orch = make_orch(tmp_path)
    with pytest.raises(RuntimeError):
        orch.resume({"action": "approve"})  # IDLE 态 resume 非法


def test_run_while_waiting_raises(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")  # WAITING_HUMAN
    with pytest.raises(RuntimeError):
        orch.run("新输入")  # 等待中重入非法


# ═══════════ 事件链完整性（修正 A）═══════════


def test_event_chain_integrity(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(analysis=LOW_CONF))
    orch.run("选A还是B")
    orch.resume({"action": "approve"})
    orch.resume({"action": "approve"})
    events = orch.events
    assert events[0].state_from == "IDLE"
    assert events[-1].state_to == "DONE"
    for a, b in zip(events, events[1:]):
        assert a.state_to == b.state_from  # 无跳变：状态转移连续
    assert all(e.seq == i + 1 for i, e in enumerate(events))  # 序号连续


def test_rerun_from_done_starts_fresh_turn(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="复盘"))
    r1 = orch.run("复盘一下")
    assert r1.status == "done"
    n_events_first = len(orch.events)

    r2 = orch.run("再复盘一次")  # DONE 等新输入：重开回合
    assert r2.status == "done"
    assert len(orch.events) == n_events_first  # 轨迹清零，不混入上一回合
    assert orch.events[0].state_from == "DONE"  # 转移自 DONE → INGEST
    assert orch.events[0].state_to == "INGEST"


def test_rerun_from_error_starts_fresh_turn(tmp_path):
    orch = make_orch(tmp_path)
    r1 = orch.run("   ")  # 空输入 → ERROR
    assert r1.status == "error"

    r2 = orch.run("选A还是B")  # ERROR 后同样可重开新回合
    assert r2.status == "waiting_human"
    assert orch.events[0].state_from == "ERROR"
    assert orch.events[0].state_to == "INGEST"


# ═══════════ 各标签路由 ═══════════


def test_practice_label_writes_todo(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="实践", draft=TODO_DRAFT))
    r1 = orch.run("要询价")
    assert r1.interrupt["kind"] == "confirm"
    r2 = orch.resume({"action": "approve"})
    assert r2.output["written"] is True
    notes = todo_notes(tmp_path)
    assert len(notes) == 1
    assert "次日跟进" in notes[0].read_text(encoding="utf-8")


def test_review_label_no_interrupt_no_write(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="复盘"))
    r = orch.run("复盘一下最近决策")
    assert r.status == "done"  # 复盘只读不写：一次跑完，无中断
    assert r.interrupt is None
    assert r.output["missing"] == ["某决策 缺少关联问题"]
    assert r.output["related"][0]["title"] == "相关经验"
    assert memo_notes(tmp_path) == [] and todo_notes(tmp_path) == []


def test_input_label_finishes_with_note(tmp_path):
    orch = make_orch(tmp_path, ScriptedEngine(label="输入"))
    r = orch.run("随手记一句话")
    assert r.status == "done"
    assert r.output["label"] == "输入"
    assert "note" in r.output  # M1 仅打标；深化见 M2/M3
    assert r.output["related"]  # 仍附召回
