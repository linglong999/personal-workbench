import pytest

from workbench.ai.skills.base import SkillContext
from workbench.mcp_server import create_server


@pytest.mark.asyncio
async def test_server_has_tools():
    # 只列工具不调用：ctx 组件用 None 占位（工具实现才需要真组件）
    server = create_server(SkillContext(engine=None, vault=None, vector=None))
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert "search_knowledge" in names
    assert "create_note" in names
    assert "classify_text" in names
    assert "scan_decision_closed_loop" in names
    assert "reopen_task" in names
