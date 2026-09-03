"""端点测试共享辅助：独立鉴权 + fake 组件，替代 bridge 的模块级单例。

bridge 的模块级单例（vector / vault / skill_ctx）以真实 cfg 构建，
业务端点测试要用 fake 替换它们，绝不触碰真实 Vault / Chroma / Obsidian 注册表（外部 IO）。
每次端点测试都用独立 db 独立 secret（monkeypatch bridge.auth_service）。
"""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import workbench.bridge as bridge
from workbench.ai.skills.base import SkillContext
from workbench.bridge import app

TEST_USER = "tester"
TEST_PASS = "pw12345"

_app_client = TestClient(app)


def app_test_client() -> TestClient:
    return _app_client


def fresh_auth_token(monkeypatch, tmp_path) -> str:
    """重建独立 auth_service（独立 db 独立 secret），返回注册后 token。"""
    svc = bridge.AuthService(
        str(tmp_path / f"auth-{uuid.uuid4().hex[:6]}.db"), secret=b"t" * 32
    )
    monkeypatch.setattr(bridge, "auth_service", svc)
    r = _app_client.post(
        "/api/auth/register", json={"username": TEST_USER, "password": TEST_PASS}
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


class FakeVector:
    """替换 bridge.vector：search 返回带空 path（避免触发 Obsidian URI 真实 IO）。"""

    def search(self, query, top_k):
        return [{"id": "c1", "title": "历史经验A", "path": ""}]

    def add(self, doc_id, title, content, path=""):
        return None


class FakeVault:
    def __init__(self, tmp_path):
        self._tmp = tmp_path

    def list_tags(self):
        return {"RAG": [{"title": "卡片A", "path": ""}]}

    def read_all_notes(self, folder):
        return []  # review Skill 扫描的入口：空库无缺失项（断言走 ScriptEngine）

    def create_note(self, folder, title, content):
        # 返回一个可 str() / 有 stem 的临时路径，不落盘
        return Path(self._tmp) / f"{folder}-{title}-1.md"


class ScriptEngine:
    """skill_ctx 的引擎替换：三旧端点（classify/review 入口）所需的确定性输出。"""

    def classify(self, text):
        return "决策备忘"

    def check_closed_loop(self, decisions):
        return ["决策 xx 缺关联问题"]


def fake_skill_ctx(tmp_path) -> SkillContext:
    """替换 bridge.skill_ctx：classify/scan/reopen 三端点的确定性 ctx。"""
    return SkillContext(engine=ScriptEngine(), vault=FakeVault(str(tmp_path)), vector=FakeVector())
