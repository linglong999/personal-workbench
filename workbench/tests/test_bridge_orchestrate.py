"""M1-B5 主管入口测试：POST /api/orchestrate + /api/orchestrate/resume。

CaseEngine/CaseVector（eval 的脚本化引擎）替换 bridge.skill_ctx，真 VaultStore 落
tmp_path——不碰真 LLM/Vault；trace_store 换 tmp（不写 .data/traces）。
会话注册表不变式：终态即删 → resume 404（HTTP 侧永远不撞 RuntimeError）。
"""

from helpers import app_test_client, fresh_auth_token

import workbench.bridge as bridge
from workbench.ai.eval import CaseEngine, CaseVector
from workbench.ai.skills.base import SkillContext
from workbench.ai.trace import TraceStore
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

client = app_test_client()


def _authed(monkeypatch, tmp_path) -> dict:
    return {"Authorization": f"Bearer {fresh_auth_token(monkeypatch, tmp_path)}"}


def _wire(monkeypatch, tmp_path):
    """脚本化接线：skill_ctx（CaseEngine + 真 Vault tmp）+ trace_store（tmp）。"""
    monkeypatch.setattr(
        bridge,
        "skill_ctx",
        SkillContext(
            CaseEngine(DECISION_SCRIPT), VaultStore(str(tmp_path / "vault")), CaseVector(DECISION_SCRIPT)
        ),
    )
    monkeypatch.setattr(bridge, "trace_store", TraceStore(tmp_path / "traces"))


def test_orchestrate_requires_auth():
    r = client.post("/api/orchestrate", json={"text": "选A还是B"})
    assert r.status_code == 401


def test_orchestrate_resume_requires_auth():
    r = client.post("/api/orchestrate/resume", json={"run_id": "x", "decision": {}})
    assert r.status_code == 401


def test_orchestrate_happy_confirm_then_approve(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    r1 = client.post(
        "/api/orchestrate", json={"text": "选A还是B"}, headers=_authed(monkeypatch, tmp_path)
    )
    assert r1.status_code == 200
    body = r1.json()
    assert body["status"] == "waiting_human"
    assert body["state"] == "WAITING_HUMAN"
    assert body["run_id"]
    assert body["interrupt"]["kind"] == "confirm"
    assert body["interrupt"]["payload"]["preview"]["title"] == "选A方案"  # 预览可直接展示
    # M2-B1：link 决策随 confirm payload 透出（相关经验 0.9 命中 auto 档）
    assert body["interrupt"]["payload"]["links"] == ["相关经验"]
    assert body["interrupt"]["payload"]["pending_review"] == []
    assert [e["event"] for e in body["events"]][-1] == "interrupt"  # 事件链随响应透出

    r2 = client.post(
        "/api/orchestrate/resume",
        json={"run_id": body["run_id"], "decision": {"action": "approve"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r2.status_code == 200
    done = r2.json()
    assert done["status"] == "done"
    assert done["state"] == "DONE"
    assert done["output"]["written"] is True
    assert done["interrupt"] is None
    assert done["output"]["related"][0]["title"] == "相关经验"  # recall 收尾随回合返回

    notes = list((tmp_path / "vault" / "决策备忘").glob("*.md"))
    assert len(notes) == 1  # 草稿不落盘 + 确认后写一次
    body_text = notes[0].read_text(encoding="utf-8")
    assert "关联问题" in body_text
    assert "[[相关经验]]" in body_text  # M2-B1：确认写入的卡带自动双链


def test_orchestrate_trace_persisted(tmp_path, monkeypatch):
    """B4 观测层接线：终态后 trace 落盘（bridge 的 .data/traces 同机制，此处 tmp）。"""
    _wire(monkeypatch, tmp_path)
    r1 = client.post(
        "/api/orchestrate", json={"text": "选A还是B"}, headers=_authed(monkeypatch, tmp_path)
    )
    run_id = r1.json()["run_id"]
    client.post(
        "/api/orchestrate/resume",
        json={"run_id": run_id, "decision": {"action": "approve"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    t = TraceStore(tmp_path / "traces").load(run_id)
    assert t.meta["status"] == "done"
    assert t.events[-1]["event"] == "finish"


def test_orchestrate_reject_not_written(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    r1 = client.post(
        "/api/orchestrate", json={"text": "选A还是B"}, headers=_authed(monkeypatch, tmp_path)
    )
    run_id = r1.json()["run_id"]
    r2 = client.post(
        "/api/orchestrate/resume",
        json={"run_id": run_id, "decision": {"action": "reject"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r2.json()["status"] == "done"
    assert r2.json()["output"].get("written") is not True
    assert list((tmp_path / "vault" / "决策备忘").glob("*.md")) == []  # 安全默认：驳回不写


def test_orchestrate_resume_unknown_run_404(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    r = client.post(
        "/api/orchestrate/resume",
        json={"run_id": "no-such-run", "decision": {"action": "approve"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r.status_code == 404


def test_orchestrate_resume_after_done_404(tmp_path, monkeypatch):
    """终态会话即删：done 后再 resume → 404（而非 500/RuntimeError）。"""
    _wire(monkeypatch, tmp_path)
    r1 = client.post(
        "/api/orchestrate", json={"text": "选A还是B"}, headers=_authed(monkeypatch, tmp_path)
    )
    run_id = r1.json()["run_id"]
    client.post(
        "/api/orchestrate/resume",
        json={"run_id": run_id, "decision": {"action": "approve"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    r2 = client.post(
        "/api/orchestrate/resume",
        json={"run_id": run_id, "decision": {"action": "approve"}},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r2.status_code == 404


def test_orchestrate_empty_input_turn_error(tmp_path, monkeypatch):
    """空输入：回合错误是数据（200 + status=error），不是传输错误。"""
    _wire(monkeypatch, tmp_path)
    r = client.post(
        "/api/orchestrate", json={"text": "   "}, headers=_authed(monkeypatch, tmp_path)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["state"] == "ERROR"
    assert body["output"]["error"] == "empty_input"
