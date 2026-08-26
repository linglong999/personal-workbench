"""Task 2-8 Mock 端到端冒烟：用 FakeLLM 走通 5 个 MCP 工具 + 价值循环。

不触碰真实 Vault / 不调用真实 LLM。临时 Vault + 临时 Chroma，隔离运行。
流程：输入捕获→分类(用户拍板)→决策→实践→复盘(闭环检查)→再实践(经验回流)。
"""
import asyncio
import tempfile
from pathlib import Path

from workbench.knowledge.vector import VectorStore
from workbench.ai.engine import AIEngine
from workbench.ai.agents import ClassifierAgent, ReviewerAgent, CoachAgent
from workbench.mcp_server import create_server


class FakeLLM:
    """返回固定结构但不真正联网的假 LLM。"""

    def complete(self, system, user):
        if "分类" in system:
            return "决策与策略"
        return "【Mock LLM】已处理"


class FakeEngine:
    """假引擎：覆盖 classify 与 check_closed_loop，模拟确认型升级机制。"""

    def __init__(self):
        self.llm = FakeLLM()
        self._ai = AIEngine(self.llm)

    def classify(self, text):
        if "说不清" in text:
            return "低置信：我拿不准归属，候选=[想法|知识卡片]，请确认后再归档"
        return "决策与策略"

    def check_closed_loop(self, decisions):
        problems = []
        for d in decisions:
            if "关联问题" not in d:
                problems.append(f"{d} 缺少关联问题 → 需补齐回填")
        return problems


def seed_vector(temp_dir: Path) -> VectorStore:
    """把几条简单"历史经验"塞进临时向量库：闭环靠规则文本命中，不依赖 embedding 语义。"""
    vs = VectorStore(str(temp_dir / "chroma"))
    seeds = [
        ("经验1", "复盘·原则", "做技术选型决策前，必须先列出至少两个候选并写清取舍。"),
        ("经验2", "知识卡片·双链", "让经验回流的关键：开新任务时主动检索历史，而不是等用户来搜。"),
        ("经验3", "复盘·偏差", "遇到说不清归属的内容，应升级到人来拍板，不要硬归档。"),
    ]
    for cid, title, content in seeds:
        vs.add(f"seed-{cid}", title, content)
    return vs


def build_mock_server(temp_dir: Path):
    engine = FakeEngine()
    vector = seed_vector(temp_dir)
    ctx = {
        "vault_path": str(temp_dir / "vault"),
        "chroma_dir": str(temp_dir / "chroma"),
        "classifier": ClassifierAgent(engine),
        "reviewer": ReviewerAgent(engine),
        "coach": CoachAgent(engine, vector),
    }
    return create_server(ctx)


async def call(server, name: str, **args):
    result = await server.call_tool(name, args)
    payload = getattr(result, "structured_content", None)
    if payload is not None:
        return payload, result.is_error
    text_attr = getattr(result, "content", None)
    if text_attr is not None and text_attr:
        return text_attr[0].text, result.is_error
    return result, getattr(result, "is_error", False)


async def main():
    print("=" * 62)
    print("Task 2-8 · Mock 端到端冒烟（FakeLLM + 临时库，不污染真实 Vault）")
    print("=" * 62)

    temp_dir = Path(tempfile.mkdtemp(prefix="wb-e2e-mock-"))
    print("（临时工作目录：", temp_dir, "，进程退出由系统回收）")
    server = build_mock_server(temp_dir)

    print("\n[1/6] 输入捕获层 · classify_text")
    payload, is_err = await call(server, "classify_text", text="有没有更适合我的卡牌游戏框架？")
    print("  →", payload)
    assert not is_err and "决策" in str(payload)

    print("\n[2/6] 决策层 · create_note（低置信升级到人 → 用户拍板后归档）")
    note = """# 决策备忘：卡牌框架选型
type: 决策备忘
关联问题: [[框架难题]]
# 结构化追问
1. 主要排障点是什么？
2. 量化指标怎么定？
# 多维度分析
- 成本 / 学习曲线 / 生态
# 结论（用户拍板）
先用 Pygame 原型验证，再评估 Godot。
"""
    payload, is_err = await call(server, "create_note", folder="决策备忘", title="卡牌框架选型", content=note)
    print("  → 已写入", payload)
    assert not is_err and "决策备忘" in str(payload)

    print("\n[3/6] 决策闭环检查 · scan_decision_closed_loop（复盘 Agent 主动驱动）")
    # 造一条缺『关联问题』的决策备忘做对照 → 应被列入问题清单
    payload, is_err = await call(server, "create_note", folder="决策备忘", title="孤决策A", content="# 决策备忘：孤决策A\ntype: 决策备忘\n# 结论\n还没想清楚")
    assert not is_err
    payload, is_err = await call(server, "scan_decision_closed_loop")
    text = payload if isinstance(payload, str) else str(payload)
    print("  → 当前问题清单:", text)
    assert not is_err and "孤决策A" in text

    print("\n[4/6] 知识库检索 · search_knowledge")
    payload, is_err = await call(server, "search_knowledge", query="技术选型 取舍", top_k=2)
    items = payload.get("result", []) if isinstance(payload, dict) else payload
    print("  → 命中", len(items), "条:", [x["title"] for x in items])
    assert not is_err and len(items) >= 1

    print("\n[5/6] 再实践 · reopen_task（Coach Agent 主动递送历史经验）")
    payload, is_err = await call(server, "reopen_task", task="新任务：又要做技术选型", top_k=2)
    items = payload.get("result", []) if isinstance(payload, dict) else payload
    print("  → 主动送回:", [x["title"] for x in items])
    assert not is_err and len(items) >= 1

    print("\n[6/6] 全库盘点（create_note 白名单校验）")
    import fastmcp.exceptions as fe
    try:
        payload, is_err = await call(server, "create_note", folder="乱写的目录", title="x", content="y")
        print("  → 非白名单目录未被拒绝！")
        assert False
    except fe.ToolError as exc:
        print("  → 非白名单目录已被拒绝（ToolError: " + str(exc) + "）✓")

    print("\n" + "=" * 62)
    print("Mock 端到端冒烟：全部走通 ✓")
    print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())