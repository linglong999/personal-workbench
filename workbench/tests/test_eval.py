"""M1-B4 eval 测试：golden case runner（通过/失败/运行时异常）+ 坏例回流 + golden 目录全量回归。

golden 目录（evals/golden/）扫出即跑——回流产物落这里，golden case 即 CI 回归。
"""

from pathlib import Path

from workbench.ai.eval import (
    CaseEngine,
    CaseVector,
    GoldenCase,
    case_from_trace,
    load_cases,
    run_case,
    run_cases,
)
from workbench.ai.orchestrator import Orchestrator
from workbench.ai.skills.base import SkillContext
from workbench.ai.trace import TraceStore
from workbench.knowledge.vault import VaultStore

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "evals" / "golden"

HIGH_CONF = {
    "question": "选A还是B",
    "dimensions": ["成本"],
    "options": [{"name": "A", "pros": "快", "cons": "糙"}],
    "clarify": [],
    "lean": "倾向A",
    "confidence": 0.85,
}
LOW_CONF = {**HIGH_CONF, "options": [], "clarify": ["预算是多少？"], "lean": "", "confidence": 0.3}
MEMO_DRAFT = {"title": "选A方案", "content": "## 背景\n…\n## 决定\n选A\n## 关联问题\n1. 成本可控？"}


def happy_case():
    return GoldenCase(
        id="t_decision",
        name="决策确认写入",
        input="选A还是B",
        script={"label": "决策", "analysis": HIGH_CONF, "draft": MEMO_DRAFT},
        resumes=[{"action": "approve"}],
        expect={
            "status": "done",
            "output": {"label": "决策", "written": True},
            # M2-B1：草稿 → recall 候选 → link → confirm → 写入 → recall 收尾
            "tools": ["classify", "decision", "action", "recall", "link", "action", "recall"],
        },
    )


# ═══════════ run_case：通过 / 失败 / 运行时异常 ═══════════


def test_run_case_pass(tmp_path):
    result = run_case(happy_case(), tmp_path)
    assert result.passed
    assert result.failures == []


def test_run_case_fail_reports_reason(tmp_path):
    case = happy_case()
    case.expect["status"] = "error"  # 故意错
    result = run_case(case, tmp_path)
    assert not result.passed
    assert any("status" in f for f in result.failures)


def test_run_case_output_mismatch(tmp_path):
    case = happy_case()
    case.expect["output"]["written"] = False  # 故意错
    result = run_case(case, tmp_path)
    assert not result.passed
    assert any("output.written" in f for f in result.failures)


def test_run_case_tools_mismatch(tmp_path):
    case = happy_case()
    case.expect["tools"] = ["classify"]  # 故意缺
    result = run_case(case, tmp_path)
    assert not result.passed
    assert any("tools" in f for f in result.failures)


def test_run_case_events_mismatch(tmp_path):
    case = happy_case()
    case.expect["events"] = ["ingest"]  # 故意缺
    result = run_case(case, tmp_path)
    assert not result.passed
    assert any("events" in f for f in result.failures)


def test_run_case_judgement_two_resumes(tmp_path):
    case = GoldenCase(
        id="t_judgement",
        name="低置信拍板后确认写入",
        input="选A还是B",
        script={"label": "决策", "analysis": LOW_CONF, "draft": MEMO_DRAFT},
        resumes=[{"action": "approve"}, {"action": "approve"}],  # judgement → confirm 双 resume
        expect={"status": "done", "output": {"written": True}},
    )
    result = run_case(case, tmp_path)
    assert result.passed, result.failures


def test_run_case_invalid_resume_is_failure_not_crash(tmp_path):
    case = happy_case()
    case.script = {"label": "复盘", "review_missing": []}  # 复盘一次跑完，无等待
    case.resumes = [{"action": "approve"}]  # resume 在 DONE 态非法
    result = run_case(case, tmp_path)
    assert not result.passed
    assert any("runtime" in f for f in result.failures)


def test_run_case_rejects_path_escaping_id(tmp_path):
    for bad in ("../evil", "a/b", "a\\b"):
        case = happy_case()
        case.id = bad
        result = run_case(case, tmp_path)
        assert not result.passed
        assert any("非法 case id" in f for f in result.failures)


def test_run_cases_report(tmp_path):
    ok = happy_case()
    bad = happy_case()
    bad.id = "t_bad"
    bad.expect["status"] = "error"
    report = run_cases([ok, bad], tmp_path)
    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
    assert "1/2" in report.summary()


# ═══════════ GoldenCase 序列化 ═══════════


def test_golden_case_json_roundtrip(tmp_path):
    case = happy_case()
    p = tmp_path / "case.json"
    p.write_text(
        case.to_json(), encoding="utf-8"
    )
    loaded = load_cases(p)
    assert loaded == [case]


# ═══════════ 坏例回流：trace → case → 重放 ═══════════


def test_case_from_trace_reflow(tmp_path):
    script = {
        "label": "乱码输出",
        "draft": {"title": "联系供应商", "content": "## 下一步\n询价\n## 次日跟进\n明早10点"},
    }
    ctx = SkillContext(
        CaseEngine(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    orch.run("要询价")
    orch.resume({"action": "pick", "label": "实践"})
    r3 = orch.resume({"action": "approve"})
    assert r3.output["written"] is True

    trace = store.load(orch.run_id)
    case = case_from_trace(trace, case_id="reflow_practice", name="实践路径回流回归")

    assert case.input == "要询价"
    assert case.script["label"] == "乱码输出"  # 从 classify step 提取
    assert case.script["draft"]["title"] == "联系供应商"  # 从 action 预览提取
    assert case.resumes == [
        {"action": "pick", "label": "实践"},
        {"action": "approve"},
    ]  # 从 resume 事件提取
    assert case.expect["status"] == "done"  # expect 从结果起草
    assert case.expect["output"]["written"] is True
    assert "path" not in case.expect["output"]  # tmp 路径不入 expect

    replay = run_case(case, tmp_path / "replay")  # 重放通过 = 行为固化
    assert replay.passed, replay.failures


def test_case_from_trace_error_run(tmp_path):
    ctx = SkillContext(
        CaseEngine({}), VaultStore(str(tmp_path / "vault")), CaseVector({})
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    orch.run("   ")  # 空输入 → ERROR

    case = case_from_trace(store.load(orch.run_id), case_id="reflow_err")
    assert case.expect["status"] == "error"
    assert case.expect["output"]["error"] == "empty_input"
    assert run_case(case, tmp_path / "replay").passed


def test_case_from_trace_decision_extraction(tmp_path):
    """decision 路径回流：analysis 提取要去 needs_judgement（重放由 Skill 重新推导）。"""
    script = {"label": "决策", "analysis": LOW_CONF, "draft": MEMO_DRAFT}
    ctx = SkillContext(
        CaseEngine(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    orch.run("选A还是B")
    orch.resume({"action": "reject"})  # 低置信 → judgement 驳回

    case = case_from_trace(store.load(orch.run_id), case_id="reflow_decision")
    assert case.script["analysis"]["confidence"] == 0.3
    assert "needs_judgement" not in case.script["analysis"]
    assert case.resumes == [{"action": "reject"}]
    assert run_case(case, tmp_path / "replay").passed


def test_case_from_trace_review_extraction(tmp_path):
    script = {"label": "复盘", "review_missing": ["孤决策 缺少关联问题"]}
    ctx = SkillContext(
        CaseEngine(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    orch.run("复盘一下")

    case = case_from_trace(store.load(orch.run_id), case_id="reflow_review")
    assert case.script["review_missing"] == ["孤决策 缺少关联问题"]
    assert case.script["related"][0]["title"] == "相关经验"  # recall 结果也脚本化
    assert run_case(case, tmp_path / "replay").passed


def test_case_from_trace_extracts_judges(tmp_path):
    """M2-B1：LLM 档判断回流——judged 明细提取为 script.judges，重放精确复现。"""
    script = {
        "label": "决策",
        "analysis": HIGH_CONF,
        "draft": MEMO_DRAFT,
        "related": [{"id": "c1", "title": "成本考量", "content": "各方案成本", "score": 0.8}],
        "judges": {"成本考量": {"link_to": True, "confidence": 0.8}},
    }
    ctx = SkillContext(
        CaseEngine(script), VaultStore(str(tmp_path / "vault")), CaseVector(script)
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    r1 = orch.run("选A还是B")
    assert r1.interrupt["payload"]["links"] == ["成本考量"]  # 0.8 → LLM 档 → judge 通过
    orch.resume({"action": "approve"})

    case = case_from_trace(store.load(orch.run_id), case_id="reflow_judged")
    assert case.script["judges"]["成本考量"] == {"link_to": True, "confidence": 0.8}
    replay = run_case(case, tmp_path / "replay")
    assert replay.passed, replay.failures
    # 重放写入的卡同样带 judge 通过的双链（行为固化）
    notes = list((tmp_path / "replay" / "case-reflow_judged" / "vault" / "决策备忘").glob("*.md"))
    assert "[[成本考量]]" in notes[0].read_text(encoding="utf-8")


def test_case_from_trace_waiting_snapshot(tmp_path):
    """等待中的快照回流：无 resume、expect=waiting，重放在同一点中断。"""
    ctx = SkillContext(
        CaseEngine({"label": "决策", "analysis": HIGH_CONF, "draft": MEMO_DRAFT}),
        VaultStore(str(tmp_path / "vault")),
        CaseVector({}),
    )
    store = TraceStore(tmp_path / "traces")
    orch = Orchestrator(ctx, trace=store)
    orch.run("选A还是B")  # 停在 confirm interrupt

    case = case_from_trace(store.load(orch.run_id), case_id="reflow_wait")
    assert case.resumes == []
    assert case.expect == {"status": "waiting_human"}
    assert run_case(case, tmp_path / "replay").passed


def test_load_cases_missing_path():
    assert load_cases(Path("no/such/dir")) == []


# ═══════════ golden 目录：CI 回归 ═══════════


def test_golden_dir_all_pass(tmp_path):
    cases = load_cases(GOLDEN_DIR)
    assert len(cases) >= 5  # 5 初始 case，回流只增不减
    report = run_cases(cases, tmp_path)
    assert report.failed == 0, report.summary()
