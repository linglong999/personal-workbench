import pytest
from workbench.mcp_server import create_server


@pytest.mark.asyncio
async def test_server_has_tools(tmp_path):
    server = create_server({"chroma_dir": str(tmp_path / "chroma")})
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert "search_knowledge" in names
    assert "create_note" in names
    assert "classify_text" in names
    assert "scan_decision_closed_loop" in names
    assert "reopen_task" in names