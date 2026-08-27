from workbench.main import build_server


def test_build_server(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    server = build_server()
    assert server.name == "workbench"