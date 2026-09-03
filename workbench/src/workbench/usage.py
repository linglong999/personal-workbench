"""调用观测注册表：记录每次工具调用与 LLM token 用量（供前端「用量」页）。

M4-B1 起存储升级为 SQLite（默认 .data/usage.db）：重启不丢、明细永存
（MAX_EVENTS 退役）、日快照支撑长期趋势——写时 upsert 与明细同一事务
（决策 8），趋势直查快照表不重算全表，快照缺失日从明细聚合兜底。
归因（决策 10）：skill 显式参数记在 llm 行、source（端点名）记在 tool 行
——不用 contextvars（FastAPI 同步 handler 跑线程池，隐式上下文会丢）。
日界全部 Python 侧计算（决策 9）：SQL 不用 date('now')（SQLite 默认 UTC）。
连接 per-call + WAL（决策 11，对齐 auth/repository 库内先例）。
价格单位：元 / 百万 tokens，从 .env 可配（LLM_PRICE_IN_PER_M / LLM_PRICE_OUT_PER_M）。
"""

import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

_prices = {"in_per_m": 1.0, "out_per_m": 2.0}  # 默认按 DeepSeek deepseek-chat 近似价，可 .env 覆盖
_db_path = ".data/usage.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    skill TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    system TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    llm_delta INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success'
);
CREATE TABLE IF NOT EXISTS daily_usage_snapshots (
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    skill TEXT NOT NULL DEFAULT '',
    total_requests INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (date, kind, source, skill)
);
"""

_SNAPSHOT_UPSERT = """
INSERT INTO daily_usage_snapshots
    (date, kind, source, skill, total_requests, input_tokens, output_tokens, cost)
VALUES (?, ?, ?, ?, 1, ?, ?, ?)
ON CONFLICT (date, kind, source, skill) DO UPDATE SET
    total_requests = total_requests + 1,
    input_tokens = input_tokens + excluded.input_tokens,
    output_tokens = output_tokens + excluded.output_tokens,
    cost = cost + excluded.cost
"""


def set_db(path: str) -> None:
    """指向指定 SQLite 文件（测试用 tmp_path 隔离；默认 .data/usage.db）。"""
    global _db_path
    _db_path = str(path)


def set_prices(in_per_m: float, out_per_m: float):
    _prices["in_per_m"] = float(in_per_m)
    _prices["out_per_m"] = float(out_per_m)


def _cost(pt: int, ct: int) -> float:
    return pt / 1e6 * _prices["in_per_m"] + ct / 1e6 * _prices["out_per_m"]


def _connect() -> sqlite3.Connection:
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)  # 幂等：set_db 换文件后无需手动建表
    return conn


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _display_ts(ts: str) -> str:
    """events 响应沿用内存版展示格式（月-日 时:分:秒）——形状不变（决策 12）。"""
    try:
        return datetime.fromisoformat(ts).strftime("%m-%d %H:%M:%S")
    except ValueError:
        return ts


def record_llm(
    model: str,
    system: str,
    user: str,
    prompt_tokens: int,
    completion_tokens: int,
    skill: str = "",
):
    """LLMClient.complete 每次调用后记录；skill 归因显式传入（决策 10）。

    明细 + 当日快照 upsert 同一事务（决策 8）：快照即当日终值。
    """
    cost = _cost(prompt_tokens, completion_tokens)
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO usage_records (ts, kind, source, skill, model, name, detail, system,"
            " input_tokens, output_tokens, cost, latency_ms, llm_delta, status)"
            " VALUES (?, 'llm', '', ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, 'success')",
            (
                _now(),
                skill,
                model,
                model,
                (user or "")[:80],
                (system or "")[:40],
                prompt_tokens,
                completion_tokens,
                round(cost, 6),
            ),
        )
        conn.execute(
            _SNAPSHOT_UPSERT,
            (date.today().isoformat(), "llm", "", skill, prompt_tokens, completion_tokens, round(cost, 6)),
        )


def snapshot() -> dict:
    """Bridge 中间件在请求前后各取一次，diff 出本次请求消耗的 tokens。"""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(input_tokens), 0) AS pt,"
            " COALESCE(SUM(output_tokens), 0) AS ct FROM usage_records WHERE kind = 'llm'"
        ).fetchone()
        return {"llm_calls": row["n"], "pt": row["pt"], "ct": row["ct"]}


def record_tool(tool: str, input_head: str, before: dict, after: dict, ms: int, ok: bool):
    """Bridge 中间件在请求结束时记录一次工具调用（含该请求触发的 LLM 增量）。

    tool 行的 pt/ct 是 LLM 增量（展示用）——快照 upsert 只 +1 请求数、
    tokens/cost 加 0：唯一事实源是 llm 行，避免全表聚合双算。
    """
    pt = max(after.get("pt", 0) - before.get("pt", 0), 0)
    ct = max(after.get("ct", 0) - before.get("ct", 0), 0)
    n_llm = max(after.get("llm_calls", 0) - before.get("llm_calls", 0), 0)
    status = "success" if ok else "error"
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO usage_records (ts, kind, source, skill, model, name, detail, system,"
            " input_tokens, output_tokens, cost, latency_ms, llm_delta, status)"
            " VALUES (?, 'tool', ?, '', '', ?, ?, '', ?, ?, ?, ?, ?, ?)",
            (_now(), tool, tool, (input_head or "")[:80], pt, ct, round(_cost(pt, ct), 6), ms, n_llm, status),
        )
        conn.execute(
            _SNAPSHOT_UPSERT,
            (date.today().isoformat(), "tool", tool, "", 0, 0, 0.0),
        )


def report() -> dict:
    """供 /api/usage 返回：汇总 + 最近事件（时间倒序）。

    totals 走快照全表聚合（决策 12：口径从"本进程"升级为"全部历史"）；
    响应形状与内存版一致（前端零改动）。
    """
    with closing(_connect()) as conn:
        llm = conn.execute(
            "SELECT COALESCE(SUM(total_requests), 0) AS calls, COALESCE(SUM(input_tokens), 0) AS pt,"
            " COALESCE(SUM(output_tokens), 0) AS ct, COALESCE(SUM(cost), 0.0) AS cost"
            " FROM daily_usage_snapshots WHERE kind = 'llm'"
        ).fetchone()
        tool = conn.execute(
            "SELECT COALESCE(SUM(total_requests), 0) AS calls"
            " FROM daily_usage_snapshots WHERE kind = 'tool'"
        ).fetchone()
        rows = conn.execute(
            "SELECT * FROM usage_records ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return {
        "prices": dict(_prices),
        "totals": {
            "tool_calls": tool["calls"],
            "llm_calls": llm["calls"],
            "prompt_tokens": llm["pt"],
            "completion_tokens": llm["ct"],
            "cost": round(llm["cost"], 6),
        },
        "events": [_event(r) for r in rows],
    }


def _event(r: sqlite3.Row) -> dict:
    ev = {
        "ts": _display_ts(r["ts"]),
        "kind": r["kind"],
        "name": r["name"],
        "detail": r["detail"],
        "pt": r["input_tokens"],
        "ct": r["output_tokens"],
        "cost": round(r["cost"], 6),
    }
    if r["kind"] == "llm":
        ev["system"] = r["system"]
    else:
        ev["ms"] = r["latency_ms"]
        ev["llm"] = r["llm_delta"]
        ev["ok"] = r["status"] == "success"
    return ev


def daily_trend(days: int = 7) -> list[dict]:
    """日趋势（B2 /api/stats 数据源）：[{date, requests, input_tokens, output_tokens, cost}]。

    LLM 用量口径（requests = llm 调用数）：快照表直查（决策 8）；
    快照缺失日从明细聚合兜底（迁移/异常场景）；缺失日补零（决策 13）。
    日界 Python 侧算（决策 9），SQL 只做字符串前缀分组。
    """
    today = date.today()
    start = today - timedelta(days=days - 1)
    wanted = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    with closing(_connect()) as conn:
        snaps: dict[str, dict] = {
            r["date"]: {
                "requests": r["requests"],
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "cost": r["cost"],
            }
            for r in conn.execute(
                "SELECT date, SUM(total_requests) AS requests, SUM(input_tokens) AS input_tokens,"
                " SUM(output_tokens) AS output_tokens, SUM(cost) AS cost"
                " FROM daily_usage_snapshots WHERE kind = 'llm' AND date >= ? GROUP BY date",
                (wanted[0],),
            )
        }
        missing = [d for d in wanted if d not in snaps]
        for r in conn.execute(
            "SELECT substr(ts, 1, 10) AS d, COUNT(*) AS requests, SUM(input_tokens) AS input_tokens,"
            " SUM(output_tokens) AS output_tokens, SUM(cost) AS cost"
            " FROM usage_records WHERE kind = 'llm' AND ts >= ? AND ts < ? GROUP BY substr(ts, 1, 10)",
            (wanted[0], f"{wanted[-1]}~"),  # '~' > 任何 ISO 时间字符：含末日全天
        ):
            if r["d"] in missing:
                snaps[r["d"]] = {
                    "requests": r["requests"],
                    "input_tokens": r["input_tokens"],
                    "output_tokens": r["output_tokens"],
                    "cost": r["cost"],
                }
    zero = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
    return [{"date": d, **snaps.get(d, zero)} for d in wanted]


def reset():
    """测试与手动清零：清明细与快照两表。"""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM usage_records")
        conn.execute("DELETE FROM daily_usage_snapshots")
