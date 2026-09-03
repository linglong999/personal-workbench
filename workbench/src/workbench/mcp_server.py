"""FastMCP 服务器：注册知识库与 AI Skill 工具。

M1-B5 起 Agent 角色退役，classify/scan/reopen 经 Skill 注册表派发
（与 bridge 同一注册表，行为同源）。
"""

from fastmcp import FastMCP

from workbench.ai.skills.base import SkillContext
from workbench.ai.skills.registry import get_skill


def create_server(ctx: SkillContext) -> FastMCP:
    mcp = FastMCP("workbench")

    @mcp.tool()
    def search_knowledge(query: str, top_k: int = 5) -> list[dict]:
        """在知识库中检索相关内容（数据层）。"""
        return ctx.vector.search(query, top_k)

    @mcp.tool()
    def create_note(folder: str, title: str, content: str) -> str:
        """在指定目录创建笔记（写入后同步向量索引，立即可检索）。"""
        path = ctx.vault.create_note(folder, title, content)
        ctx.vector.add(f"note-{path.stem}", title, content, path=str(path))
        return str(path)

    @mcp.tool()
    def classify_text(text: str) -> str:
        """对输入内容分类打标（classify Skill）。"""
        return get_skill("classify").run(ctx, {"text": text}).output["label"]

    @mcp.tool()
    def scan_decision_closed_loop() -> list[str]:
        """扫描决策闭环率，找出缺少关联问题的决策（review Skill 主动驱动）。"""
        return get_skill("review").run(ctx, {}).output["missing"]

    @mcp.tool()
    def reopen_task(task: str, top_k: int = 5) -> list[dict]:
        """开新任务时主动递送历史经验（recall Skill 驱动）。"""
        return get_skill("recall").run(ctx, {"task": task, "top_k": top_k}).output["results"]

    return mcp
