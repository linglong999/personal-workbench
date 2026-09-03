"""M1-B4 trace 测试：TraceStore 落盘/回放/校验/归因 + 主管接线 + 修正 A（观测层失败不杀任务）。

引擎/向量用 eval 的 CaseEngine/CaseVector（同一确定性脚本机制，golden 回放一致）；
Vault 用真 VaultStore 落盘（B2 教训：写路径必须测真契约）。
"""

import pytest

from workbench.ai.eval import CaseEngine, CaseVector
from workbench.ai.orchestrator import Orchestrator
from workbench.ai.skills.base import SkillContext
from workbench.ai.trace import TraceStore, attribute_failure, verify
from workbench.knowledge.vault import VaultStore

DECISION_SCRIPT = {
    "label": "决策",
    "analysis": {
        "question": "选A还是B",
        "dimensions": ["成本"],
        "options": [{"name": "A", "pros": "快", "cons": "糙"}],
        "clarify": [],
        "lean": "倾向A",
        "confidence": 0.85,
    },
    "draft": {
        "title": "选A方案",
        "content": "## 背景\n…\n## 决定\n选A\n## 关联问题\n1. 成本可控？",
    },
}
LOW_CONF_SCRIPT = {
    **DECISION_SCRIPT,
    "analysis": {**DECISION_SCRIPT["analysis"], "confidence": 0.3},
}


def make_orch(tmp_path, script=None, store=None):
    script = script or DECISION_SCRIPT
    ctx = SkillContext(
        CaseEngine(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    trace = store or TraceStore(tmp_path / "traces")
    return Orchestrator(ctx, trace=trace)


def memo_notes(tmp_path):
    return list((tmp_path / "vault" / "决策备忘").glob("*.md"))


# ═══════════ 落盘 / 回放（roundtrip）═══════════


def test_save_load_roundtrip(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    orch.resume({"action": "approve"})

    store = TraceStore(tmp_path / "traces")
    t = store.load(orch.run_id)
    assert t.meta["input"] == "选A还是B"
    assert t.meta["status"] == "done"
    assert len(t.events) == len(orch.events)  # 完整链
    assert t.events[0]["event"] == "ingest"
    assert t.events[-1]["event"] == "finish"
    assert t.events[2]["tool"] == "classify"  # dict 形态字段可读（观测层不认 DomainEvent 类）
    assert t.events[2]["result"]["label"] == "决策"
    assert t.events[-1]["result"]["written"] is True


def test_waiting_snapshot_then_resume_overwrites_same_run(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")  # 首个观测点：WAITING_HUMAN 快照

    store = TraceStore(tmp_path / "traces")
    t1 = store.load(orch.run_id)
    assert t1.meta["status"] == "waiting_human"
    assert t1.events[-1]["event"] == "interrupt"

    first_id = orch.run_id
    orch.resume({"action": "approve"})  # 续写同回合 → 同 run_id 覆盖
    assert orch.run_id == first_id
    t2 = store.load(first_id)
    assert t2.meta["status"] == "done"
    assert t2.events[-1]["event"] == "finish"
    assert len(t2.events) > len(t1.events)  # 覆盖为终态完整链
    assert len(list((tmp_path / "traces").glob("*.json"))) == 1  # 一个回合一个文件


def test_rerun_new_run_id_keeps_old_file(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    orch.resume({"action": "approve"})
    id1 = orch.run_id

    orch.run("选A还是B")  # DONE 后重开新回合
    orch.resume({"action": "approve"})
    id2 = orch.run_id
    assert id2 != id1

    store = TraceStore(tmp_path / "traces")
    runs = store.list_runs()
    assert len(runs) == 2
    assert [r["run_id"] for r in runs] == sorted([id1, id2], reverse=True)  # 最新在前
    assert store.load(id1).meta["input"] == "选A还是B"  # 旧回合保留


def test_list_runs_empty_dir(tmp_path):
    assert TraceStore(tmp_path / "nope").list_runs() == []


def test_save_without_run_id_raises(tmp_path):
    with pytest.raises(ValueError):
        TraceStore(tmp_path / "traces").save({"input": "x"}, [])


# ═══════════ 链完整性校验（回放验证）═══════════


def test_verify_good_chain(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    orch.resume({"action": "approve"})
    t = TraceStore(tmp_path / "traces").load(orch.run_id)
    assert verify(t.events) == []


def test_verify_broken_chain_reports_problems(tmp_path):
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    orch.resume({"action": "approve"})
    t = TraceStore(tmp_path / "traces").load(orch.run_id)

    jump = [dict(e) for e in t.events]
    jump[3]["state_from"] = "MARS"  # 状态跳变
    assert any("状态跳变" in p for p in verify(jump))

    seq = [dict(e) for e in t.events]
    seq[2]["seq"] = 99  # 序号断裂
    assert any("seq" in p for p in verify(seq))

    first = [dict(e) for e in t.events]
    first[0]["state_from"] = "ACTING"  # 首事件不合法
    assert any("首事件" in p for p in verify(first))

    assert verify([]) == ["空事件链"]


def test_verify_truncated_tail(tmp_path):
    """链在 step 处截断（末事件停在 ACTING）→ 报"末事件停在"问题。"""
    orch = make_orch(tmp_path)
    orch.run("选A还是B")
    orch.resume({"action": "approve"})
    t = TraceStore(tmp_path / "traces").load(orch.run_id)
    truncated = t.events[:3]  # ingest, act, step —— 停在 ACTING
    assert any("末事件停在" in p for p in verify(truncated))


# ═══════════ 归因（坏例定位）═══════════


def test_attribute_error_run(tmp_path):
    class BoomEngine(CaseEngine):
        def classify(self, text):
            raise RuntimeError("LLM down")

    ctx = SkillContext(
        BoomEngine(DECISION_SCRIPT),
        VaultStore(str(tmp_path / "vault")),
        CaseVector(DECISION_SCRIPT),
    )
    orch = Orchestrator(ctx, trace=TraceStore(tmp_path / "traces"))
    r = orch.run("选A还是B")
    assert r.status == "error"

    t = TraceStore(tmp_path / "traces").load(orch.run_id)
    att = attribute_failure(t.events)
    assert att["kind"] == "error"
    assert "LLM down" in att["reason"]
    assert att["tool"] == ""  # 出错前无 step（classify 即崩）
    assert att["at_seq"] == t.events[-1]["seq"]


def test_attribute_error_after_steps_points_last_tool(tmp_path):
    class LateBoom(CaseEngine):
        def draft_note(self, kind, text):  # classify/decision 成功，起草时崩
            raise RuntimeError("draft 失败")

    script = {**DECISION_SCRIPT}
    ctx = SkillContext(
        LateBoom(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    orch = Orchestrator(ctx, trace=TraceStore(tmp_path / "traces"))
    orch.run("选A还是B")

    t = TraceStore(tmp_path / "traces").load(orch.run_id)
    att = attribute_failure(t.events)
    assert att["kind"] == "error"
    assert att["tool"] == "decision"  # 出错前最后成功的 step
    assert "draft 失败" in att["reason"]


def test_attribute_low_confidence_steps(tmp_path):
    orch = make_orch(tmp_path, LOW_CONF_SCRIPT)
    orch.run("选A还是B")
    orch.resume({"action": "reject"})  # 驳回 → done 无 error

    t = TraceStore(tmp_path / "traces").load(orch.run_id)
    att = attribute_failure(t.events)
    assert att["kind"] == "ok"
    assert att["low_confidence"][0]["tool"] == "decision"
    assert att["low_confidence"][0]["confidence"] == 0.3


# ═══════════ 修正 A 灵魂测试：观测层失败不杀任务 ═══════════


def test_trace_write_failure_does_not_kill_task(tmp_path):
    class ExplodingStore(TraceStore):
        def save(self, meta, events):
            raise OSError("disk full")

    ctx = SkillContext(
        CaseEngine(DECISION_SCRIPT),
        VaultStore(str(tmp_path / "vault")),
        CaseVector(DECISION_SCRIPT),
    )
    orch = Orchestrator(ctx, trace=ExplodingStore(tmp_path / "traces"))

    r1 = orch.run("选A还是B")  # 落盘炸了 → 任务照常中断等待
    assert r1.status == "waiting_human"
    r2 = orch.resume({"action": "approve"})  # 续跑也炸 → 任务照常完成
    assert r2.status == "done"
    assert r2.output["written"] is True
    assert len(memo_notes(tmp_path)) == 1  # 业务副作用不受观测层影响
