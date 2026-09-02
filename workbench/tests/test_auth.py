import pytest

from workbench.auth.repository import UserRepository
from workbench.auth.service import AuthService, hash_password, verify_password


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "auth.db")


def test_hash_and_verify():
    h = hash_password("secret123")
    assert h != "secret123"
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_repo_create_get(db):
    repo = UserRepository(db)
    repo.create_user("alice", hash_password("pw"))
    u = repo.get_by_username("alice")
    assert u is not None and u.username == "alice"
    assert u.password_hash != "pw"


def test_repo_duplicate_username(db):
    repo = UserRepository(db)
    repo.create_user("bob", hash_password("pw"))
    with pytest.raises(ValueError):
        repo.create_user("bob", hash_password("pw2"))


def test_auth_register_login(db):
    svc = AuthService(db, secret=b"t" * 32, ttl_seconds=3600)
    token = svc.register("carol", "pw12345")
    assert isinstance(token, str) and token
    me = svc.authenticate("carol", "pw12345")
    assert me.username == "carol"


def test_auth_wrong_password(db):
    svc = AuthService(db, secret=b"t" * 32)
    svc.register("dave", "pw12345")
    with pytest.raises(ValueError):
        svc.authenticate("dave", "badpw")


def test_verify_token_roundtrip(db):
    svc = AuthService(db, secret=b"t" * 32)
    token = svc.register("erin", "pw12345")
    payload = svc.verify_token(token)
    assert payload["sub"] == "erin"
    with pytest.raises(ValueError):
        svc.verify_token("not-a-token")


def test_register_short_password(db):
    svc = AuthService(db, secret=b"t" * 32)
    with pytest.raises(ValueError):
        svc.register("frank", "12345")


def test_remember_extends_ttl(db):
    svc = AuthService(db, secret=b"t" * 32, ttl_seconds=3600)
    svc.register("grace", "pw12345")
    short = svc.verify_token(svc.login("grace", "pw12345", remember=False))
    long = svc.verify_token(svc.login("grace", "pw12345", remember=True))
    assert short["exp"] - short["iat"] == 3600
    assert long["exp"] - long["iat"] == 30 * 24 * 3600


def test_register_remember_extends_ttl(db):
    svc = AuthService(db, secret=b"t" * 32, ttl_seconds=3600)
    token = svc.register("heidi", "pw12345", remember=True)
    payload = svc.verify_token(token)
    assert payload["exp"] - payload["iat"] == 30 * 24 * 3600
