"""FastMCP 服务器：注册知识库与 AI / Agent 工具。"""

from fastmcp import FastMCP

from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore


def create_server(ctx) -> FastMCP:
    vault = VaultStore(ctx.get("vault_path", ""))
    vector = VectorStore(ctx.get("chroma_dir", ".data/chroma"))
    classifier = ctx.get("classifier")
    reviewer = ctx.get("reviewer")
    coach = ctx.get("coach")

    mcp = FastMCP("workbench")

    @mcp.tool()
    def search_knowledge(query: str, top_k: int = 5) -> list[dict]:
        """在知识库中检索相关内容（数据层）。"""
        return vector.search(query, top_k)

    @mcp.tool()
    def create_note(folder: str, title: str, content: str) -> str:
        """在指定目录创建笔记（写入后同步向量索引，立即可检索）。"""
        path = vault.create_note(folder, title, content)
        vector.add(f"note-{path.stem}", title, content, path=str(path))
        return str(path)

    @mcp.tool()
    def classify_text(text: str) -> str:
        """对输入内容分类打标（输入层 Agent）。"""
        return classifier.classify(text)

    @mcp.tool()
    def scan_decision_closed_loop() -> list[str]:
        """扫描决策闭环率，找出缺少关联问题的决策（复盘层 Agent 主动驱动）。"""
        return reviewer.scan_closed_loop(vault)

    @mcp.tool()
    def reopen_task(task: str, top_k: int = 5) -> list[dict]:
        """开新任务时主动递送历史经验（再实践层 Coach Agent 驱动）。"""
        return coach.recall_for_task(task, top_k)

    return mcp
