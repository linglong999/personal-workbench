from fastapi.testclient import TestClient

import workbench.bridge as bridge
from workbench.bridge import app

client = TestClient(app)


def test_health_open():
    """health 端点放行（不鉴权）。"""
    r = client.get("/api/health")
    assert r.status_code == 200


def test_unauthenticated_blocked():
    """业务端点未带 token → 401。"""
    r = client.post("/api/search_knowledge", json={"query": "x"})
    assert r.status_code == 401


def test_invalid_token_blocked():
    """伪造 token → 401。"""
    r = client.post(
        "/api/search_knowledge", json={"query": "x"}, headers={"Authorization": "Bearer bad"}
    )
    assert r.status_code == 401


def test_register_login_me_flow(tmp_path, monkeypatch):
    # 独立 db + 独立 secret，避免污染 .data/app.db；require_auth 走同一 auth_service（单源）
    monkeypatch.setattr(
        bridge, "auth_service", bridge.AuthService(str(tmp_path / "a.db"), secret=b"t" * 32)
    )
    r = client.post("/api/auth/register", json={"username": "u1", "password": "pw12345"})
    assert r.status_code == 200
    token = r.json()["token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "u1"


def test_login_wrong_password(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bridge, "auth_service", bridge.AuthService(str(tmp_path / "a.db"), secret=b"t" * 32)
    )
    client.post("/api/auth/register", json={"username": "u2", "password": "pw12345"})
    r = client.post("/api/auth/login", json={"username": "u2", "password": "wrongpw"})
    assert r.status_code == 401


def test_register_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bridge, "auth_service", bridge.AuthService(str(tmp_path / "a.db"), secret=b"t" * 32)
    )
    client.post("/api/auth/register", json={"username": "u3", "password": "pw12345"})
    r = client.post("/api/auth/register", json={"username": "u3", "password": "pw12345"})
    assert r.status_code == 400
