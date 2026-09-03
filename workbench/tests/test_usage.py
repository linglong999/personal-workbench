"""usage 观测模块测试：SQLite 持久化（M4-B1）——记录/聚合/快照/趋势/重开不丢。

契约锁定（决策 12）：report() 响应形状与内存版完全一致（前端零改动）；
totals 口径从"本进程"升级为"全部历史"；明细永存（MAX_EVENTS 退役）。
归因（决策 10）：skill 记 llm 行、source 记 tool 行，显式参数贯穿。
快照（决策 8）：record 与当日 upsert 同事务；趋势直查快照 + 明细兜底补齐。
日界（决策 9）：Python 侧算，SQL 不用 date('now')。
"""

import sqlite3

from workbench import usage


def _db(tmp_path) -> str:
    path = str(tmp_path / "usage.db")
    usage.set_db(path)
    return path


def _rows(path: str, sql: str, params=()) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ═══════════ 原有行为契约（形状不变，锁死）═══════════


def test_record_llm_and_report_totals(tmp_path):
    _db(tmp_path)
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


def test_llm_event_shape_unchanged(tmp_path):
    """决策 12：事件条目字段集与内存版逐字段一致（llm 行含 system、无 ms/llm/ok）。"""
    _db(tmp_path)
    usage.record_llm("m", "sys文本", "用户输入", 100, 50, skill="classify")
    ev = usage.report()["events"][0]
    assert set(ev) == {"ts", "kind", "name", "detail", "system", "pt", "ct", "cost"}
    assert ev["system"] == "sys文本"
    assert ev["detail"] == "用户输入"
    assert ev["ts"]  # 展示格式（月-日 时:分:秒），非空即可——格式见时间测试


def test_tool_event_shape_unchanged(tmp_path):
    _db(tmp_path)
    before = usage.snapshot()
    usage.record_llm("m", "s", "u", 500, 100)
    usage.record_tool("/api/classify_text", "输入头", before, usage.snapshot(), 42, True)
    ev = usage.report()["events"][0]
    assert set(ev) == {"ts", "kind", "name", "detail", "ms", "llm", "pt", "ct", "cost", "ok"}
    assert ev["kind"] == "tool"
    assert ev["pt"] == 500 and ev["ct"] == 100  # 仅请求触发的增量
    assert ev["llm"] == 1
    assert ev["ms"] == 42
    assert ev["ok"] is True


def test_record_tool_clamps_negative_delta(tmp_path):
    _db(tmp_path)
    before = {"llm_calls": 50, "pt": 9999, "ct": 9999}
    after = {"llm_calls": 3, "pt": 100, "ct": 50}
    usage.record_tool("/api/x", "", before, after, 5, False)
    ev = usage.report()["events"][0]
    assert ev["pt"] == 0 and ev["ct"] == 0 and ev["llm"] == 0
    assert ev["cost"] == 0.0
    assert ev["ok"] is False


def test_report_latest_first_up_to_50(tmp_path):
    _db(tmp_path)
    for i in range(60):
        usage.record_llm("m", "sys", f"u{i}", 1, 0)
    events = usage.report()["events"]
    assert len(events) == 50  # report 只回最近 50 条
    assert events[0]["detail"].startswith("u59")  # 时间倒序


def test_reset_clears_state(tmp_path):
    _db(tmp_path)
    usage.record_llm("m", "sys", "u", 10, 5)
    usage.record_tool("/api/x", "", usage.snapshot(), usage.snapshot(), 1, True)
    usage.reset()
    r = usage.report()
    assert r["events"] == []
    assert r["totals"]["llm_calls"] == 0
    assert r["totals"]["tool_calls"] == 0
    assert r["totals"]["cost"] == 0.0


# ═══════════ M4-B1 · SQLite 持久化与归因 ═══════════


def test_records_persist_across_reopen(tmp_path):
    """重启不丢：换进程视角（重新 set_db 同一路径）数据仍在，totals 全史口径。"""
    path = _db(tmp_path)
    usage.set_prices(1.0, 2.0)
    usage.record_llm("deepseek-chat", "s", "u", 1000, 500)
    usage.record_tool("/api/x", "", usage.snapshot(), usage.snapshot(), 1, True)
    usage.set_db(path)  # 模拟重启：同一文件重新打开
    r = usage.report()
    assert r["totals"]["llm_calls"] == 1
    assert r["totals"]["tool_calls"] == 1
    assert r["totals"]["prompt_tokens"] == 1000
    assert len(r["events"]) == 2  # 时间线跨重启仍在


def test_records_not_capped(tmp_path):
    """决策 12：MAX_EVENTS 退役，明细永存（200+ 条不丢最旧）。"""
    _db(tmp_path)
    for i in range(250):
        usage.record_llm("m", "sys", f"u{i}", 1, 0)
    assert usage.report()["totals"]["llm_calls"] == 250  # 全史计数


def test_skill_attribution_on_llm_row(tmp_path):
    """决策 10：record_llm 的 skill 记在明细行（显式参数贯穿，非 contextvars）。"""
    path = _db(tmp_path)
    usage.record_llm("deepseek-chat", "s", "u", 10, 5, skill="classify")
    rows = _rows(path, "SELECT skill, source, kind FROM usage_records")
    assert rows == [{"skill": "classify", "source": "", "kind": "llm"}]


def test_source_attribution_on_tool_row(tmp_path):
    """决策 10：source 由 middleware 按端点名记在 tool 行。"""
    path = _db(tmp_path)
    usage.record_tool("/api/classify_text", "头", usage.snapshot(), usage.snapshot(), 3, True)
    rows = _rows(path, "SELECT source, skill, kind, status FROM usage_records")
    assert rows == [{"source": "/api/classify_text", "skill": "", "kind": "tool", "status": "success"}]


def test_daily_snapshot_written_with_record(tmp_path):
    """决策 8：record_llm 与当日快照 upsert 同一事务（写时更新，快照即终值）。"""
    path = _db(tmp_path)
    usage.set_prices(1.0, 2.0)
    usage.record_llm("m", "s", "u", 1000, 500, skill="classify")
    usage.record_llm("m", "s", "u2", 2000, 500, skill="classify")
    rows = _rows(path, "SELECT * FROM daily_usage_snapshots")
    assert len(rows) == 1  # 同日同 skill 只一行（upsert 累加）
    row = rows[0]
    assert row["total_requests"] == 2
    assert row["input_tokens"] == 3000
    assert row["output_tokens"] == 1000
    assert row["cost"] == round(3000 / 1e6 * 1.0 + 1000 / 1e6 * 2.0, 6)


def test_tool_calls_counted_in_snapshot_without_token_double_count(tmp_path):
    """tool 行进快照只 +1 请求数：tokens/cost 是 LLM 增量重复，不得二次累加。"""
    path = _db(tmp_path)
    before = usage.snapshot()
    usage.record_llm("m", "s", "u", 1000, 500)
    usage.record_tool("/api/x", "", before, usage.snapshot(), 3, True)
    snaps = _rows(path, "SELECT kind, total_requests, input_tokens, cost FROM daily_usage_snapshots")
    tool_snap = next(s for s in snaps if s["kind"] == "tool")
    llm_snap = next(s for s in snaps if s["kind"] == "llm")
    assert tool_snap["total_requests"] == 1
    assert tool_snap["input_tokens"] == 0  # 不重复计 token
    assert tool_snap["cost"] == 0.0
    assert llm_snap["input_tokens"] == 1000  # tokens 唯一事实源 = llm 行
    assert usage.report()["totals"]["prompt_tokens"] == 1000  # 全表聚合无双算


# ═══════════ M4-B1 · 日趋势（B2 /api/stats 数据源）═══════════


def _fake_history(path: str, day_iso: str, skill: str = "classify") -> None:
    """伪造历史数据：改明细 ts + 快照 date 到指定日（绕开 now() 便于测跨日）。"""
    import sqlite3 as s3

    with s3.connect(path) as conn:
        conn.execute("UPDATE usage_records SET ts = ?", (f"{day_iso}T10:00:00",))
        conn.execute("UPDATE daily_usage_snapshots SET date = ?", (day_iso,))
        _ = skill  # skill 维度不影响按日聚合断言


def test_daily_trend_from_snapshot(tmp_path):
    """趋势直查快照表（决策 8）：昨日有量、今日有量 → 两点 + 其余补零。"""
    path = _db(tmp_path)
    usage.set_prices(1.0, 2.0)
    usage.record_llm("m", "s", "u", 1000, 500, skill="classify")
    from datetime import date as d
    from datetime import timedelta

    yesterday = (d.today() - timedelta(days=1)).isoformat()
    _fake_history(path, yesterday)
    usage.record_llm("m", "s", "u2", 200, 100, skill="classify")  # 今日新调用
    trend = usage.daily_trend(7)
    assert len(trend) == 7  # 缺失日补零（决策 13）
    assert trend[-1]["date"] == d.today().isoformat()  # 含今日
    assert trend[-1]["input_tokens"] == 200
    assert trend[-2]["date"] == yesterday
    assert trend[-2]["input_tokens"] == 1000
    assert trend[0]["requests"] == 0  # 无数据日为零


def test_daily_trend_backfills_from_records_when_snapshot_missing(tmp_path):
    """快照缺失日从明细聚合兜底（迁移/异常场景，决策 8）。"""
    path = _db(tmp_path)
    usage.record_llm("m", "s", "u", 1000, 500, skill="classify")
    import sqlite3 as s3

    with s3.connect(path) as conn:  # 模拟快照缺失（旧版数据只有明细）
        conn.execute("DELETE FROM daily_usage_snapshots")
    trend = usage.daily_trend(1)
    assert trend[0]["requests"] == 1
    assert trend[0]["input_tokens"] == 1000
    assert trend[0]["cost"] == round(1000 / 1e6 * 1.0 + 500 / 1e6 * 2.0, 6)  # 与明细行同式


def test_daily_trend_empty_days_zero(tmp_path):
    _db(tmp_path)
    trend = usage.daily_trend(7)
    assert len(trend) == 7
    assert all(t["requests"] == 0 and t["cost"] == 0.0 for t in trend)
