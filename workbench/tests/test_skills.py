"""M1-B1 Skill 基础设施测试：协议 + 注册表 + 3 个迁移 Skill 的等价性证明。

等价断言（迁移无回归的机制）：同一 fake 输入下，Skill.run 输出与现有 Agent
输出一致——agents.py 本批不动（bridge 兼容），逻辑迁入 skills，两路对照防漂移。
"""

import pytest

from workbench.ai.agents import ClassifierAgent, CoachAgent, ReviewerAgent
from workbench.ai.skills.base import Skill, SkillContext
from workbench.ai.skills.registry import REGISTRY, get_skill
from workbench.knowledge.vault import VaultStore


class FakeEngine:
    def classify(self, text):
        return "决策"

    def check_closed_loop(self, decisions):
        return [f"{d} 缺少关联问题" for d in decisions if "关联问题" not in d]


class FakeVector:
    def search(self, query, top_k):
        return [{"id": "n1", "title": "历史经验", "score": 0.9}][:top_k]


def make_ctx(tmp_path):
    return SkillContext(
        engine=FakeEngine(),
        vault=VaultStore(str(tmp_path)),
        vector=FakeVector(),
    )


def test_registry_has_migrated_skills():
    assert set(REGISTRY) == {"classify", "review", "recall"}  # B2 补 decision/action 成 5


def test_get_skill_returns_protocol_instances():
    for name in REGISTRY:
        s = get_skill(name)
        assert isinstance(s, Skill)
        assert s.name == name
        assert s.description
        assert s.requires_confirmation is False  # 3 个迁移 Skill 均默认自主


def test_get_skill_unknown_raises():
    with pytest.raises(KeyError):
        get_skill("nope")


def test_classify_skill_equivalent_to_agent(tmp_path):
    ctx = make_ctx(tmp_path)
    result = get_skill("classify").run(ctx, {"text": "我该选哪个方案"})
    agent_label = ClassifierAgent(ctx.engine).classify("我该选哪个方案")
    assert result.output["label"] == agent_label == "决策"
    assert result.confidence == 1.0


def test_review_skill_equivalent_to_agent(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.vault.create_note("决策备忘", "孤决策", "---\ntype: 决策备忘\n---")
    result = get_skill("review").run(ctx, {})
    agent_missing = ReviewerAgent(ctx.engine).scan_closed_loop(ctx.vault)
    assert result.output["missing"] == agent_missing
    assert len(result.output["missing"]) == 1  # read_all_notes 返回内容；孤决策缺关联 → 1 条
    assert "缺少关联问题" in result.output["missing"][0]


def test_recall_skill_equivalent_to_agent(tmp_path):
    ctx = make_ctx(tmp_path)
    result = get_skill("recall").run(ctx, {"task": "复盘上一个项目", "top_k": 3})
    agent_results = CoachAgent(ctx.engine, ctx.vector).recall_for_task("复盘上一个项目", 3)
    assert result.output["results"] == agent_results
    assert result.output["results"][0]["title"] == "历史经验"
