"""AI 引擎：分类打标、追问、提炼等能力。"""


class AIEngine:
    def __init__(self, llm):
        self.llm = llm

    def classify(self, text: str) -> str:
        system = (
            "你是分类助手。根据内容判断类型，只输出 '输入'、'决策'、'实践'、'复盘'、'创造' 之一。"
        )
        return self.llm.complete(system, text)

    def check_closed_loop(self, decisions: list[str]) -> list[str]:
        """检查决策闭环率：返回缺少关联的决策问题清单。实际实现可调用 LLM 语义判断，此处按规则返回。"""
        problems = []
        for d in decisions:
            if "关联问题" not in d:
                problems.append(f"{d} 缺少关联问题")
        return problems
