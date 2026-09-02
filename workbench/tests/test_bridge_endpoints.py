"""业务端点覆盖（方案 A 收口语）：7 个业务端点 happy path + 鉴权拒访。

这些端点是前端 LIVE 模式每天在调的 API 契约，但此前只有鉴权路径有测试，
端点本体零回归防线。用 fake 组件替换模块级单例（见 conftest），不碰外部 IO。

观测中间件 observe_calls 会为每个业务 POST 记录一条 usage 事件——内存态、无副作用，
测试不依赖其计数。
"""

import pytest
from helpers import (
    FakeClassifier,
    FakeCoach,
    FakeReviewer,
    FakeVault,
    FakeVector,
    app_test_client,
    fresh_auth_token,
)

from workbench import usage


@pytest.fixture()
def client():
    return app_test_client()


def _authed(monkeypatch, tmp_path) -> dict:
    return {"Authorization": f"Bearer {fresh_auth_token(monkeypatch, tmp_path)}"}


def test_search_knowledge_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.vector", FakeVector())
    monkeypatch.setattr("workbench.bridge._obsidian_uri", lambda p: "")
    r = client.post(
        "/api/search_knowledge",
        json={"query": "优先级", "top_k": 3},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["id"] == "c1"
    assert "obsidian_uri" in body["results"][0]


def test_list_tags_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.vault", FakeVault(str(tmp_path)))
    monkeypatch.setattr("workbench.bridge._obsidian_uri", lambda p: "")
    r = client.post("/api/list_tags", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    body = r.json()
    assert "RAG" in body["tags"]
    assert body["tags"]["RAG"][0]["title"] == "卡片A"
    assert "obsidian_uri" in body["tags"]["RAG"][0]


def test_usage_happy(client, tmp_path, monkeypatch):
    usage.reset()
    r = client.get("/api/usage", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    body = r.json()
    assert "totals" in body and "events" in body and "prices" in body


def test_create_note_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.vault", FakeVault(str(tmp_path)))
    monkeypatch.setattr("workbench.bridge.vector", FakeVector())
    monkeypatch.setattr("workbench.bridge._obsidian_uri", lambda p: "")
    r = client.post(
        "/api/create_note",
        json={"folder": "决策备忘", "title": "测试", "content": "# 正文"},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["indexed"] is True
    assert body["path"].endswith(".md")


def test_classify_text_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.classifier", FakeClassifier())
    r = client.post(
        "/api/classify_text",
        json={"text": "今天要做一个决策"},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r.status_code == 200
    assert r.json()["label"] == "决策备忘"


def test_scan_decision_closed_loop_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.reviewer", FakeReviewer())
    r = client.post(
        "/api/scan_decision_closed_loop", json={}, headers=_authed(monkeypatch, tmp_path)
    )
    assert r.status_code == 200
    assert "缺关联问题" in r.json()["missing"][0]


def test_reopen_task_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.coach", FakeCoach())
    r = client.post(
        "/api/reopen_task", json={"task": "复盘上一个项目"}, headers=_authed(monkeypatch, tmp_path)
    )
    assert r.status_code == 200
    assert r.json()["results"][0]["title"] == "历史经验A"


def test_business_endpoint_requires_auth(client, tmp_path, monkeypatch):
    """业务端点未带 token 一律 401，即使 fake 了组件（鉴权优先于逻辑）。"""
    monkeypatch.setattr("workbench.bridge.vector", FakeVector())
    r = client.post("/api/search_knowledge", json={"query": "x"})
    assert r.status_code == 401


def test_invalid_token_401(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.vector", FakeVector())
    r = client.post(
        "/api/search_knowledge",
        json={"query": "x"},
        headers={"Authorization": "Bearer garbage"},
    )
    assert r.status_code == 401
