"""M2-B2 · hash 增量索引测试：真 VaultStore + 真 VectorStore（tmp_path 落盘）。

关键约定（与写卡路径互认）：
- doc_id 同款 `note-{stem}`——sync 不会给 action/create_note 写过的卡再造重复条目；
- content_hash 只算正文——写卡路径索引真实标题、sync 从文件名剥日期前缀推标题，
  若 hash 含标题，同一张卡会在两种标题间无限"更新"；
- upsert 语义不处理删除/改名（最小版约定，留全量重建）。
"""

from workbench.ai.skills.base import SkillContext
from workbench.ai.skills.registry import get_skill
from workbench.knowledge.indexer import SyncReport, sync_vault
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore, content_hash


def make_pair(tmp_path):
    vault = VaultStore(str(tmp_path / "vault"))
    vector = VectorStore(str(tmp_path / "chroma"))
    return vault, vector


class DraftEngine:
    """action 写卡路径的最小引擎替身（draft_note 可控）。"""

    def draft_note(self, kind, text):
        return {"title": "选A方案", "content": "## 背景\n…\n## 决定\n选A\n## 关联问题\n1. 成本？"}


def test_first_sync_indexes_all(tmp_path):
    vault, vector = make_pair(tmp_path)
    vault.create_note("知识卡片", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vault.create_note("决策备忘", "选A方案", "## 决定\n选A")
    report = sync_vault(vault, vector)
    assert report == SyncReport(added=2, updated=0, skipped=0)
    results = vector.search("艾森豪威尔矩阵", top_k=5)
    assert any(r["title"] == "艾森豪威尔矩阵" for r in results)  # 首次入库即可检索（日期前缀已剥）


def test_second_sync_all_skipped_zero_upserts(tmp_path, monkeypatch):
    """hash 命中零重算：二跑不触发任何 upsert（embedding 复用）。"""
    vault, vector = make_pair(tmp_path)
    vault.create_note("知识卡片", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    sync_vault(vault, vector)
    calls = []
    monkeypatch.setattr(vector.collection, "upsert", lambda **kw: calls.append(kw))
    report = sync_vault(vault, vector)
    assert report == SyncReport(added=0, updated=0, skipped=1)
    assert calls == []  # 零 upsert = 零 embedding 重算


def test_edited_card_only_updates_that_card(tmp_path, monkeypatch):
    """Obsidian 手动改一张卡：只重算该卡（upsert 恰一次），其余 skipped。"""
    vault, vector = make_pair(tmp_path)
    p1 = vault.create_note("知识卡片", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vault.create_note("知识卡片", "二八法则", "少数关键因素决定大部分结果")
    sync_vault(vault, vector)
    p1.write_text("重要且紧急，立刻做；紧急的先排程再Delegate", encoding="utf-8")

    calls = []
    real_upsert = vector.collection.upsert

    def counting_upsert(**kw):
        calls.append(kw)
        return real_upsert(**kw)

    monkeypatch.setattr(vector.collection, "upsert", counting_upsert)
    report = sync_vault(vault, vector)
    assert report == SyncReport(added=0, updated=1, skipped=1)
    assert len(calls) == 1  # 只重算被改的那张
    assert calls[0]["ids"][0].endswith("艾森豪威尔矩阵")


def test_new_card_added(tmp_path):
    vault, vector = make_pair(tmp_path)
    vault.create_note("知识卡片", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    sync_vault(vault, vector)
    vault.create_note("知识卡片", "二八法则", "少数关键因素决定大部分结果")
    report = sync_vault(vault, vector)
    assert report == SyncReport(added=1, updated=0, skipped=1)


def test_add_stores_content_hash_in_metadata(tmp_path):
    """写卡路径 metadata 带 content_hash：add 落 Chroma metadata（get_hash 不是自说自话）。"""
    vs = VectorStore(str(tmp_path / "chroma"))
    vs.add("note-x", "标题", "内容ABC")
    assert vs.get_hash("note-x") == content_hash("内容ABC")
    res = vs.collection.get(ids=["note-x"], include=["metadatas"])
    assert res["metadatas"][0]["content_hash"] == content_hash("内容ABC")


def test_action_write_then_sync_skips(tmp_path):
    """写卡路径（action 同款）写入即带 hash：sync 复用不重算——入口一致的集成证明。"""
    vault, vector = make_pair(tmp_path)
    ctx = SkillContext(DraftEngine(), vault, vector)
    get_skill("action").run(ctx, {"kind": "决策备忘", "text": "选A还是B", "confirmed": True})
    report = sync_vault(vault, vector)
    assert report == SyncReport(added=0, updated=0, skipped=1)
