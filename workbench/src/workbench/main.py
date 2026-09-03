"""应用入口：加载配置并构建 MCP 服务器。"""

from workbench.ai.engine import AIEngine
from workbench.ai.llm import LLMClient
from workbench.ai.skills.base import SkillContext
from workbench.config import load_config
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore
from workbench.mcp_server import create_server


def build_server():
    cfg = load_config()
    llm = LLMClient(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model)
    engine = AIEngine(llm)
    vector = VectorStore(cfg.chroma_dir)
    vault = VaultStore(cfg.vault_path)
    return create_server(SkillContext(engine, vault, vector))


def main():
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
