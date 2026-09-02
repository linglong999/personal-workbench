"""M1 Skill 层测试：B1 协议/注册表/迁移等价 + B2 新 Skill（decision/action）。

等价断言（迁移无回归的机制）：同一 fake 输入下，Skill.run 输出与现有 Agent
输出一致——agents.py B5 退役前两路对照防漂移。
B2 契约：interrupt 发射归 B3 主管；Skill 侧落「标志 + 未确认零副作用 + 确认后写入」。
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


def test_registry_has_five_skills():
    assert set(REGISTRY) == {"classify", "decision", "action", "review", "recall"}


def test_get_skill_returns_protocol_instances():
    expected_confirm = {
        "classify": False,
        "decision": False,
        "action": True,  # 写 Vault 副作用 → confirm interrupt（B3 主管接线）
        "review": False,
        "recall": False,
    }
    for name in REGISTRY:
        s = get_skill(name)
        assert isinstance(s, Skill)
        assert s.name == name
        assert s.description
        assert s.requires_confirmation is expected_confirm[name]


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


# ═══════════ M1-B2 · decision Skill（决策层：结构化追问 + 多维分析）═══════════


class FakeDecisionEngine(FakeEngine):
    def __init__(self, analysis):
        self.analysis = analysis

    def analyze_decision(self, text):
        return self.analysis


def decision_ctx(tmp_path, analysis):
    return SkillContext(engine=FakeDecisionEngine(analysis), vault=None, vector=None)


def test_decision_high_confidence_autonomous(tmp_path):
    analysis = {
        "question": "先做哪个功能",
        "dimensions": ["成本", "收益"],
        "options": [{"name": "A", "pros": "快", "cons": "糙"}],
        "clarify": [],
        "lean": "倾向 A：验证快",
        "confidence": 0.85,
    }
    result = get_skill("decision").run(decision_ctx(tmp_path, analysis), {"text": "先做哪个"})
    assert result.output["options"] == analysis["options"]
    assert result.output["lean"] == "倾向 A：验证快"
    assert result.output["needs_judgement"] is False  # 高置信：默认自主
    assert result.confidence == 0.85


def test_decision_low_confidence_needs_judgement(tmp_path):
    analysis = {
        "question": "先做哪个功能",
        "dimensions": [],
        "options": [],
        "clarify": ["预算是多少？"],
        "lean": "",
        "confidence": 0.3,
    }
    result = get_skill("decision").run(decision_ctx(tmp_path, analysis), {"text": "先做哪个"})
    assert result.output["needs_judgement"] is True  # 拍板标记：B3 映射 disambiguate/judgement
    assert result.output["clarify"] == ["预算是多少？"]
    assert result.confidence == 0.3


def test_decision_invalid_confidence_treated_as_zero(tmp_path):
    analysis = {"question": "q", "confidence": "garbage"}
    result = get_skill("decision").run(decision_ctx(tmp_path, analysis), {"text": "x"})
    assert result.confidence == 0.0
    assert result.output["needs_judgement"] is True  # LLM 边界：非法置信度按最低处理


# ═══════════ M1-B2 · action Skill（实践层：写库前 confirm）═══════════


class FakeActionEngine(FakeEngine):
    def __init__(self, draft):
        self.draft = draft

    def draft_note(self, kind, text):
        return self.draft


def action_ctx(tmp_path, draft):
    # 真 VaultStore：写入路径测真契约（ALLOWED_FOLDERS 白名单、落盘、读取）
    vault = VaultStore(str(tmp_path / "vault"))
    ctx = SkillContext(engine=FakeActionEngine(draft), vault=vault, vector=None)
    return ctx, vault


MEMO_DRAFT = {
    "title": "选 A 方案",
    "content": "## 背景\n...\n## 决定\n选 A\n## 关联问题\n1. A 的成本是否可控？",
}


def test_action_unconfirmed_has_no_side_effect_and_idempotent(tmp_path):
    ctx, vault = action_ctx(tmp_path, MEMO_DRAFT)
    args = {"kind": "决策备忘", "text": "决定选 A"}
    for _ in range(2):  # 重复未确认调用：零写入（幂等）
        result = get_skill("action").run(ctx, args)
        assert result.output["status"] == "needs_confirmation"
        assert result.output["title"] == "选 A 方案"  # 预览带给用户看（B3 confirm interrupt 的内容）
        assert "关联问题" in result.output["content"]
    assert vault.list_notes("决策备忘") == []


def test_action_confirmed_writes_decision_memo(tmp_path):
    ctx, vault = action_ctx(tmp_path, MEMO_DRAFT)
    result = get_skill("action").run(
        ctx, {"kind": "决策备忘", "text": "决定选 A", "confirmed": True}
    )
    assert result.output["status"] == "written"
    assert result.output["path"].endswith(".md")
    notes = vault.list_notes("决策备忘")
    assert len(notes) == 1
    assert "关联问题" in notes[0].read_text(encoding="utf-8")  # 闭环契约：review 扫描依赖该节


def test_action_confirmed_writes_todo_into_action_log(tmp_path):
    todo_draft = {"title": "联系供应商", "content": "## 下一步\n询价三家\n## 次日跟进\n明早 10 点"}
    ctx, vault = action_ctx(tmp_path, todo_draft)
    result = get_skill("action").run(
        ctx, {"kind": "待办", "text": "要询价", "confirmed": True}
    )
    assert result.output["status"] == "written"
    notes = vault.list_notes("行动记录")  # 待办 → 行动记录（Vault 白名单目录）
    assert len(notes) == 1
    assert "次日跟进" in notes[0].read_text(encoding="utf-8")


def test_action_unknown_kind_rejected_before_any_work(tmp_path):
    ctx, vault = action_ctx(tmp_path, MEMO_DRAFT)
    with pytest.raises(ValueError):  # 入口即拒绝（未确认/已确认一致），不产出预览也不写库
        get_skill("action").run(ctx, {"kind": "乱写", "text": "x", "confirmed": True})
    assert vault.list_notes("决策备忘") == []

