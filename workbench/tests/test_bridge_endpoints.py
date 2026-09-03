"""业务端点覆盖（方案 A 收口语）：7 个业务端点 happy path + 鉴权拒访。

这些端点是前端 LIVE 模式每天在调的 API 契约，但此前只有鉴权路径有测试，
端点本体零回归防线。用 fake 组件替换模块级单例（见 conftest），不碰外部 IO。

观测中间件 observe_calls 会为每个业务 POST 记录一条 usage 事件——内存态、无副作用，
测试不依赖其计数。
"""

import pytest
from helpers import (
    FakeVault,
    FakeVector,
    app_test_client,
    fake_skill_ctx,
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
    monkeypatch.setattr("workbench.bridge.skill_ctx", fake_skill_ctx(tmp_path))
    r = client.post(
        "/api/classify_text",
        json={"text": "今天要做一个决策"},
        headers=_authed(monkeypatch, tmp_path),
    )
    assert r.status_code == 200
    assert r.json()["label"] == "决策备忘"


def test_scan_decision_closed_loop_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.skill_ctx", fake_skill_ctx(tmp_path))
    r = client.post("/api/scan_decision_closed_loop", json={}, headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    assert "缺关联问题" in r.json()["missing"][0]


def test_reopen_task_happy(client, tmp_path, monkeypatch):
    monkeypatch.setattr("workbench.bridge.skill_ctx", fake_skill_ctx(tmp_path))
    r = client.post("/api/reopen_task", json={"task": "复盘上一个项目"}, headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    assert r.json()["results"][0]["title"] == "历史经验A"


def test_sync_vault_happy(client, tmp_path, monkeypatch):
    """M2-B2 增量同步端点：真组件 tmp 落盘（FakeVector 无 get_hash，与 test_vector 同款真 Chroma）。"""
    from workbench.knowledge.vault import VaultStore
    from workbench.knowledge.vector import VectorStore

    vault = VaultStore(str(tmp_path / "vault"))
    vector = VectorStore(str(tmp_path / "chroma"))
    vault.create_note("知识卡片", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    monkeypatch.setattr("workbench.bridge.vault", vault)
    monkeypatch.setattr("workbench.bridge.vector", vector)
    r = client.post("/api/sync_vault", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    assert r.json() == {"added": 1, "updated": 0, "skipped": 0}
    # 二跑全 skipped（hash 命中）：端到端增量语义
    r2 = client.post("/api/sync_vault", headers=_authed(monkeypatch, tmp_path))
    assert r2.json() == {"added": 0, "updated": 0, "skipped": 1}


def test_sync_vault_requires_auth(client):
    r = client.post("/api/sync_vault")
    assert r.status_code == 401


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


# ═══════════ M4-B2 · /api/stats 聚合端点（真组件 tmp 落盘）═══════════


def _stats_wire(monkeypatch, tmp_path):
    """替换 vault/vector 单例为 tmp 真组件（stats 扫真文件与真 Chroma，不碰真库）。"""
    from workbench.knowledge.vault import VaultStore
    from workbench.knowledge.vector import VectorStore

    monkeypatch.setattr("workbench.bridge.vault", VaultStore(str(tmp_path / "vault")))
    monkeypatch.setattr("workbench.bridge.vector", VectorStore(str(tmp_path / "chroma")))


def test_stats_requires_auth(client):
    r = client.get("/api/stats")
    assert r.status_code == 401


def test_stats_invalid_range_422(client, tmp_path, monkeypatch):
    """决策 16：range 只认 7d|30d（Literal 注解原生 422）。"""
    _stats_wire(monkeypatch, tmp_path)
    r = client.get("/api/stats?range=10d", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 422


def test_stats_unknown_include_422(client, tmp_path, monkeypatch):
    """决策 16：include 逗号分隔手动校验，未知 token 422（拼错早暴露）。"""
    _stats_wire(monkeypatch, tmp_path)
    r = client.get("/api/stats?include=knowledge,foo", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 422


def test_stats_default_both_modules(client, tmp_path, monkeypatch):
    """缺省 include=knowledge,usage：双模块键齐备，回显 range，趋势 7 点。"""
    _stats_wire(monkeypatch, tmp_path)
    r = client.get("/api/stats", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    body = r.json()
    assert body["range"] == "7d"
    assert set(body) == {"range", "knowledge", "usage"}
    assert len(body["knowledge"]["trend"]) == 7
    assert len(body["usage"]["trend"]) == 7
    assert len(body["knowledge"]["distribution"]) == 6


def test_stats_include_knowledge_only(client, tmp_path, monkeypatch):
    """include 过滤：未请求的模块键不出现（决策 19）；30d 趋势 30 点。"""
    _stats_wire(monkeypatch, tmp_path)
    r = client.get(
        "/api/stats?include=knowledge&range=30d", headers=_authed(monkeypatch, tmp_path)
    )
    body = r.json()
    assert body["range"] == "30d"
    assert "usage" not in body
    assert len(body["knowledge"]["trend"]) == 30


def test_stats_include_usage_only(client, tmp_path, monkeypatch):
    _stats_wire(monkeypatch, tmp_path)
    r = client.get("/api/stats?include=usage", headers=_authed(monkeypatch, tmp_path))
    assert r.status_code == 200
    assert "knowledge" not in r.json()
    assert len(r.json()["usage"]["trend"]) == 7
