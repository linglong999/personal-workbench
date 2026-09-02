"""调用观测注册表：记录每次工具调用与 LLM token 用量（供前端「用量」页）。

内存存储（Bridge 单进程生命周期内有效，重启清零），零依赖。
价格单位：元 / 百万 tokens，从 .env 可配（LLM_PRICE_IN_PER_M / LLM_PRICE_OUT_PER_M）。
"""

import threading
from datetime import datetime

_lock = threading.Lock()
_events: list[dict] = []  # 时间线：工具调用 + LLM 调用，按发生顺序
_totals = {"tool_calls": 0, "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}
_prices = {"in_per_m": 1.0, "out_per_m": 2.0}  # 默认按 DeepSeek deepseek-chat 近似价，可 .env 覆盖
MAX_EVENTS = 200


def set_prices(in_per_m: float, out_per_m: float):
    _prices["in_per_m"] = float(in_per_m)
    _prices["out_per_m"] = float(out_per_m)


def _cost(pt: int, ct: int) -> float:
    return pt / 1e6 * _prices["in_per_m"] + ct / 1e6 * _prices["out_per_m"]


def record_llm(model: str, system: str, user: str, prompt_tokens: int, completion_tokens: int):
    """LLMClient.complete 每次调用后记录。"""
    cost = _cost(prompt_tokens, completion_tokens)
    with _lock:
        _events.append(
            {
                "ts": datetime.now().strftime("%m-%d %H:%M:%S"),
                "kind": "llm",
                "name": model,
                "detail": (user or "")[:80],
                "system": (system or "")[:40],
                "pt": prompt_tokens,
                "ct": completion_tokens,
                "cost": round(cost, 6),
            }
        )
        _totals["llm_calls"] += 1
        _totals["prompt_tokens"] += prompt_tokens
        _totals["completion_tokens"] += completion_tokens
        _totals["cost"] = round(_totals["cost"] + cost, 6)
        if len(_events) > MAX_EVENTS:
            del _events[0]


def snapshot() -> dict:
    """Bridge 中间件在请求前后各取一次，diff 出本次请求消耗的 tokens。"""
    with _lock:
        return {
            "llm_calls": _totals["llm_calls"],
            "pt": _totals["prompt_tokens"],
            "ct": _totals["completion_tokens"],
        }


def record_tool(tool: str, input_head: str, before: dict, after: dict, ms: int, ok: bool):
    """Bridge 中间件在请求结束时记录一次工具调用（含该请求触发的 LLM 增量）。"""
    pt = max(after.get("pt", 0) - before.get("pt", 0), 0)
    ct = max(after.get("ct", 0) - before.get("ct", 0), 0)
    n_llm = max(after.get("llm_calls", 0) - before.get("llm_calls", 0), 0)
    with _lock:
        _events.append(
            {
                "ts": datetime.now().strftime("%m-%d %H:%M:%S"),
                "kind": "tool",
                "name": tool,
                "detail": (input_head or "")[:80],
                "ms": ms,
                "llm": n_llm,
                "pt": pt,
                "ct": ct,
                "cost": round(_cost(pt, ct), 6),
                "ok": ok,
            }
        )
        _totals["tool_calls"] += 1


def report() -> dict:
    """供 /api/usage 返回：汇总 + 最近事件（时间倒序）。"""
    with _lock:
        return {
            "prices": dict(_prices),
            "totals": dict(_totals),
            "events": list(reversed(_events[-50:])),
        }


def reset():
    """测试与手动清零。"""
    with _lock:
        _events.clear()
        for k in ("tool_calls", "llm_calls", "prompt_tokens", "completion_tokens"):
            _totals[k] = 0
        _totals["cost"] = 0.0
