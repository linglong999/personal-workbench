from workbench.ai.engine import AIEngine
from workbench.ai.agents import ClassifierAgent, ReviewerAgent


class FakeLLM:
    def complete(self, system, user):
        return "分类打标: 决策与策略"


def test_classify():
    engine = AIEngine(FakeLLM())
    result = engine.classify("我该选哪个方案")
    assert "决策" in result


def test_classifier_agent_uses_engine():
    agent = ClassifierAgent(AIEngine(FakeLLM()))
    assert agent.classify("我该选哪个方案") == "分类打标: 决策与策略"


def test_reviewer_agent_finds_unlinked_decisions(monkeypatch, tmp_path):
    from workbench.knowledge.vault import VaultStore
    vault = VaultStore(str(tmp_path))
    vault.create_note("决策备忘", "孤决策", "---\ntype: 决策备忘\n---")

    class FakeEngine:
        def check_closed_loop(self, decisions):
            return ["决策备忘/孤决策 缺少关联问题"]

    agent = ReviewerAgent(FakeEngine())
    problems = agent.scan_closed_loop(vault)
    assert len(problems) == 1
    assert "孤决策" in problems[0]