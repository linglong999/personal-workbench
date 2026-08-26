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