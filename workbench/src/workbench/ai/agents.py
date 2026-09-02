"""多 Agent 角色：每个 Agent 封装一种协作职责。"""

from workbench.knowledge.vault import VaultStore


class ClassifierAgent:
    """输入层 Agent：分类打标。"""

    def __init__(self, engine):
        self.engine = engine

    def classify(self, text: str) -> str:
        return self.engine.classify(text)


class ReviewerAgent:
    """复盘层 Agent：检查决策闭环率，驱动追问。"""

    def __init__(self, engine):
        self.engine = engine

    def scan_closed_loop(self, vault: VaultStore) -> list[str]:
        """扫描决策备忘，找出缺少 `关联问题` 的条目，返回问题清单。"""
        notes = vault.read_all_notes("决策备忘")
        return self.engine.check_closed_loop(notes)


class CoachAgent:
    """再实践层 Agent（产品灵魂一环）：开新任务时主动递送历史经验。

    对应 PRD"它带着经验回来"——按任务主题检索知识库（问题整理/复盘沉淀/知识卡片）
    里的历史原则与偏差提炼，主动把最相关的 2-5 条递到用户面前，而不是等用户来搜。
    """

    def __init__(self, engine, vector):
        self.engine = engine
        self.vector = vector

    def recall_for_task(self, task: str, top_k: int = 5) -> list[dict]:
        """基于任务主题做向量检索，返回最相关历史经验（标题+内容），供上游递送。"""
        return self.vector.search(task, top_k)
