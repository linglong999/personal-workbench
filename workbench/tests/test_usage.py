"""usage 观测模块（调用/LLM token/成本聚合）单元测试。

纯内存、线程锁保护、零外部依赖——直接测 record_/report/reset 的计数与成本计算。
M4 会把存储从内存升级为 SQLite，本测试锁定现有行为契约（字段、计数、成本公式）。
"""

from workbench import usage


def _reset():
    usage.reset()


def test_record_llm_and_report_totals():
    _reset()
    usage.set_prices(1.0, 2.0)
    usage.record_llm("deepseek-chat", "sys", "用户输入", 1000, 500)
    usage.record_llm("deepseek-chat", "sys", "再来一次", 2000, 250)
    r = usage.report()
    assert r["totals"]["llm_calls"] == 2
    assert r["totals"]["prompt_tokens"] == 3000
    assert r["totals"]["completion_tokens"] == 750
    # 成本 = 3000/M*1.0 + 750/M*2.0（元，保留 6 位）
    assert r["totals"]["cost"] == round(3000 / 1e6 * 1.0 + 750 / 1e6 * 2.0, 6)
    ev = r["events"][0]
    assert ev["kind"] == "llm"
    assert ev["name"] == "deepseek-chat"


def test_record_tool_diffs_llm_delta():
    _reset()
    usage.record_llm("m", "s", "u", 1000, 200)  # 请求前已经发生的调用
    before = usage.snapshot()
    usage.record_llm("m", "s", "本次调用", 500, 100)
    after = usage.snapshot()
    usage.record_tool("/api/classify_text", "输入头", before, after, 42, True)
    r = usage.report()
    ev = r["events"][0]
    assert ev["kind"] == "tool"
    assert ev["pt"] == 500 and ev["ct"] == 100  # 仅请求触发的增量
    assert ev["llm"] == 1
    assert ev["ms"] == 42
    assert ev["ok"] is True
    assert r["totals"]["tool_calls"] == 1


def test_record_tool_clamps_negative_delta():
    _reset()
    # after < before 的异常情况（理论上不发生）：差值截断为 0
    before = {"llm_calls": 50, "pt": 9999, "ct": 9999}
    after = {"llm_calls": 3, "pt": 100, "ct": 50}
    usage.record_tool("/api/x", "", before, after, 5, False)
    ev = usage.report()["events"][0]
    assert ev["pt"] == 0 and ev["ct"] == 0 and ev["llm"] == 0
    assert ev["cost"] == 0.0
    assert ev["ok"] is False


def test_events_capped_at_max():
    _reset()
    for i in range(usage.MAX_EVENTS + 20):
        usage.record_llm("m", "sys", f"u{i}", 1, 0)
    assert len(usage._events) == usage.MAX_EVENTS  # 内部时间线上限
    assert len(usage.report()["events"]) == 50  # report 只回最近 50 条


def test_report_latest_first_up_to_50():
    _reset()
    for i in range(60):
        usage.record_llm("m", "sys", f"u{i}", 1, 0)
    events = usage.report()["events"]
    assert len(events) == 50  # report 只回最近 50 条
    assert events[0]["detail"].startswith("u59")  # 时间倒序


def test_reset_clears_state():
    _reset()
    usage.record_llm("m", "sys", "u", 10, 5)
    usage.record_tool("/api/x", "", usage.snapshot(), usage.snapshot(), 1, True)
    usage.reset()
    r = usage.report()
    assert r["events"] == []
    assert r["totals"]["llm_calls"] == 0
    assert r["totals"]["tool_calls"] == 0
    assert r["totals"]["cost"] == 0.0
