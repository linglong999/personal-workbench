import pytest
from workbench.config import ConfigError, load_config


def test_load_config_with_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    cfg = load_config()
    assert cfg.vault_path == str(tmp_path)
    assert cfg.llm_api_key == "test-key"
    assert cfg.llm_model


def test_load_config_missing_vault(monkeypatch):
    monkeypatch.delenv("VAULT_PATH", raising=False)
    with pytest.raises(ConfigError):
        load_config(use_dotenv=False)