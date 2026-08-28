from workbench.knowledge.vault import VaultStore


def test_create_note(tmp_path):
    vault = VaultStore(str(tmp_path))
    path = vault.create_note("决策备忘", "测试决策", "# 标题\n内容")
    assert path.exists()
    assert "测试决策" in path.name


def test_create_note_requires_known_folder(tmp_path):
    import pytest
    vault = VaultStore(str(tmp_path))
    with pytest.raises(ValueError):
        vault.create_note("不存在的目录", "x", "y")


def test_create_note_same_title_no_overwrite(tmp_path):
    vault = VaultStore(str(tmp_path))
    p1 = vault.create_note("决策备忘", "同题", "第一条")
    p2 = vault.create_note("决策备忘", "同题", "第二条")
    assert p1 != p2
    assert p1.read_text(encoding="utf-8") == "第一条"
    assert p2.read_text(encoding="utf-8") == "第二条"


def test_list_tags_returns_title_and_path(tmp_path):
    vault = VaultStore(str(tmp_path))
    folder = tmp_path / "知识卡片"
    folder.mkdir()
    (folder / "卡片A.md").write_text(
        "---\ntitle: 卡片A\ntags:\n  - RAG\n  - Agent\n---\n\n正文", encoding="utf-8")
    (folder / "卡片B.md").write_text(
        "---\ntags:\n  - RAG\n---\n\n正文", encoding="utf-8")
    tags = vault.list_tags()
    assert set(tags.keys()) == {"RAG", "Agent"}
    assert {e["title"] for e in tags["RAG"]} == {"卡片A", "卡片B"}
    for e in tags["RAG"]:
        assert e["path"].endswith(".md") and "卡片" in e["path"]