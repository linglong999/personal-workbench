"""Task 2-8 真实验收脚本（Step1-5）：真实 Vault 索引 + 真实 LLM。

边界（按用户确认）：
- VAULT_PATH 直接用真实玲珑de知识库；测试决策写入其真实「决策备忘」目录，
  用「验收测试」前缀便于识别，验收后如需可手动清理。
- 知识卡片/（79 张）只读索引，用于 RAG；Chroma 用独立目录（.data/chroma-verify）。
"""
import asyncio
import os
from pathlib import Path
import tempfile

os.chdir(r"d:\HuaweiMoveData\Users\曹玲珑\Desktop\个人工作台\workbench")

from workbench.config import load_config
from workbench.ai.llm import LLMClient
from workbench.ai.engine import AIEngine
from workbench.ai.agents import ClassifierAgent, ReviewerAgent, CoachAgent
from workbench.knowledge.vector import VectorStore
from workbench.mcp_server import create_server

REAL_CARD_DIR = Path(r"D:\HuaweiMoveData\Users\曹玲珑\Documents\Obsidian Vault\玲珑de知识库\知识卡片")


def index_real_cards(vector: VectorStore) -> int:
    """把真实知识卡片读入向量库（只读）。"""
    n = 0
    for f in sorted(REAL_CARD_DIR.glob("*.md")):
        title = f.stem
        content = f.read_text(encoding="utf-8", errors="ignore")
        vector.add(f"card-{title}", title, content)
        n += 1
    return n


def build_server(cfg, vector: VectorStore):
    llm = LLMClient(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model)
    engine = AIEngine(llm)
    ctx = {
        "vault_path": cfg.vault_path,
        "chroma_dir": cfg.chroma_dir,
        "classifier": ClassifierAgent(engine),
        "reviewer": ReviewerAgent(engine),
        "coach": CoachAgent(engine, vector),
    }
    return create_server(ctx)


async def call(server, name: str, **args):
    result = await server.call_tool(name, args)
    sc = getattr(result, "structured_content", None)
    if sc is not None:
        return sc, result.is_error
    ct = getattr(result, "content", None)
    if ct:
        return ct[0].text, result.is_error
    return result, getattr(result, "is_error", False)


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text


async def main():
    pwd = Path.cwd()
    cfg = load_config()  # 读 .env
    print("LLM:", cfg.llm_base_url, "|", cfg.llm_model)

    print("\n[索引] 读取真实知识卡片 → Chroma (.data/chroma-verify)")
    vector = VectorStore(str(pwd / cfg.chroma_dir))
    n = index_real_cards(vector)
    print(f"  → 已索引 {n} 张卡片")
    assert n == 79

    server = build_server(cfg, vector)
    print("Server:", server.name)

    # ---- Step 2: search_knowledge（真实 RAG）----
    print("\n[Step2] search_knowledge — RAG 检索真实卡片")
    for q in ["GraphRAG 的六步流水线", "Prompt 工程的六个要素", "RAG 与幻觉的关系"]:
        sc, err = await call(server, "search_knowledge", query=q, top_k=3)
        items = sc.get("result", []) if isinstance(sc, dict) else sc
        title = items[0]["title"] if items else "—"
        print(f"  Q={q!r}")
        for it in items[:3]:
            print(f"     命中: {it['title']}")

    # ---- Step 3: classify_text（真实 LLM 分类）----
    print("\n[Step3] classify_text — 真实 LLM 分类")
    sc, err = await call(server, "classify_text", text="我决定先用 Pygame 做原型来验证卡牌框架的想法")
    print("  →", sc)

    # ---- Step 3b: scan_decision_closed_loop（沙箱内自建决策，闭环检查）----
    print("\n[Step3b] scan_decision_closed_loop — 闭环检查（写入真实决策回忆录）")
    dec_with = "# 决策备忘：验收测试决策A\ntype: 决策备忘\n关联问题: [[xxx]]\n结论: 做"
    dec_without = "# 决策备忘：验收测试决策B\ntype: 决策备忘\n结论: 待定"  # 缺关联问题
    sc, err = await call(server, "create_note", folder="决策备忘", title="验收测试决策A", content=dec_with)
    sc, err = await call(server, "create_note", folder="决策备忘", title="验收测试决策B", content=dec_without)
    sc, err = await call(server, "scan_decision_closed_loop")
    print("  → 结果:", sc)

    # ---- Step 4: reopen_task（真实 LLM + 检索，经验回流）----
    print("\n[Step4] reopen_task — 开新任务主动递送经验")
    sc, err = await call(server, "reopen_task", task="新任务：给知识库写一篇关于 RAG 的系统总结", top_k=3)
    import re
    m = re.search(r"\"result\":\s*\[(.*)\]", sc if isinstance(sc, str) else str(sc), re.S)
    print("  → 主动送回相关经验（title）:",
          [x.get("title") for x in (sc.get("result", []) if isinstance(sc, dict) else []) if isinstance(x, dict)])

    print("\n" + "=" * 60)
    print("真实验收完成 ✓")


if __name__ == "__main__":
    asyncio.run(main())