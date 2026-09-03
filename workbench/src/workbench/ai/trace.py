"""Trace 观测层：TraceStore 落盘 / 回放校验 / 归因（M1-B4，兑现 M1-A 修正 A）。

观测层与执行层类型解耦：只认 dict（JSON 形态事件），不 import DomainEvent——
orchestrator 保存时 asdict 转换，trace 零反向依赖；trace 写失败不是运行保证
（orchestrator._save_trace 静默容错，见 test_trace 修正 A 灵魂测试）。
存储：一 run 一 JSON 文件（{run_id}.json = meta + events）；run_id = 时间戳-短哈希，
文件名即排序键。
"""

import json
from dataclasses import dataclass
from pathlib import Path

from workbench.ai.skills.decision import DecisionSkill

# 终态/观测点：链允许停在这三处（WAITING_HUMAN 是回合内稳定点，可 resume 续写）
_END_STATES = ("DONE", "ERROR", "WAITING_HUMAN")


@dataclass
class Trace:
    """一个回合的观测记录：meta（run_id/input/status）+ dict 事件链。"""

    meta: dict
    events: list[dict]


class TraceStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def save(self, meta: dict, events: list[dict]) -> Path:
        run_id = str(meta.get("run_id", ""))
        if not run_id:
            raise ValueError("meta 缺 run_id")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{run_id}.json"
        path.write_text(
            json.dumps({"meta": meta, "events": events}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return path

    def load(self, run_id: str) -> Trace:
        path = self.root / f"{run_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return Trace(meta=data["meta"], events=data["events"])

    def list_runs(self) -> list[dict]:
        """列出全部回合 meta（最新在前，附 n_events）；目录不存在返回空。"""
        if not self.root.exists():
            return []
        runs = []
        for p in self.root.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            meta = dict(data["meta"])
            meta["n_events"] = len(data["events"])
            runs.append(meta)
        return sorted(runs, key=lambda m: str(m.get("run_id", "")), reverse=True)


def verify(events: list[dict]) -> list[str]:
    """事件链完整性校验（回放时事后核验）：返回问题列表，空 = 完整。"""
    problems: list[str] = []
    if not events:
        return ["空事件链"]
    if events[0].get("state_from") not in ("IDLE", "DONE", "ERROR"):
        problems.append(
            f"首事件 state_from={events[0].get('state_from')} 非 IDLE/DONE/ERROR（截断或损坏）"
        )
    for i, e in enumerate(events):
        if e.get("seq") != i + 1:
            problems.append(f"seq 不连续: 位置 {i} 为 {e.get('seq')}")
    for a, b in zip(events, events[1:]):
        if a.get("state_to") != b.get("state_from"):
            problems.append(f"状态跳变: seq {b.get('seq')} {a.get('state_to')} → {b.get('state_from')}")
    if events[-1].get("state_to") not in _END_STATES:
        problems.append(f"末事件停在 {events[-1].get('state_to')}（非终态/观测点）")
    return problems


def attribute_failure(events: list[dict]) -> dict:
    """最小归因：error 事件定位（reason + 出错前最后 tool + at_seq）+ 低置信步骤收集。"""
    last_tool = ""
    low_confidence: list[dict] = []
    for e in events:
        if e.get("event") == "step":
            last_tool = str(e.get("tool", ""))
            conf = e.get("confidence")
            if conf is not None and conf < DecisionSkill.CONFIDENCE_THRESHOLD:
                low_confidence.append({"tool": last_tool, "seq": e.get("seq"), "confidence": conf})
        if e.get("event") == "error":
            return {
                "kind": "error",
                "reason": str(e.get("reason", "")),
                "at_seq": e.get("seq"),
                "tool": last_tool,
                "low_confidence": low_confidence,
            }
    return {"kind": "ok", "low_confidence": low_confidence}
