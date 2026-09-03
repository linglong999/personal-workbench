"""M1 Skill 层测试：B1 协议/注册表/迁移 + B2 新 Skill（decision/action）+ B5 收口契约。

B1 等价测试（Skill vs Agent 两路对照）已完成防漂移使命，B5 agents.py 退役后改为
直接断言。B2 契约：interrupt 发射归主管；Skill 侧落「标志 + 未确认零副作用 + 确认后写入」。
B5 新契约：确认写入后同步向量索引（写入即索引，所有入口一致）。
M2-B1 新增：link Skill（三档阈值分流/去重/人工链排除）+ action links 渲染（## 关联节）。
"""

import re

import pytest

from workbench.ai.skills.base import Skill, SkillContext
from workbench.ai.skills.registry import REGISTRY, get_skill
from workbench.knowledge.vault import VaultStore

# 行级匹配：区分「## 关联」（双链节）与「## 关联问题」（备忘契约节）
_SECTION_LINK = re.compile(r"^## 关联$", re.MULTILINE)


class FakeEngine:
    def classify(self, text):
        return "决策"

    def check_closed_loop(self, decisions):
        return [f"{d} 缺少关联问题" for d in decisions if "关联问题" not in d]


class FakeVector:
    """search 供 recall；add 记录调用（写入即索引契约的断言依据）。"""

    def __init__(self):
        self.added: list[tuple] = []

    def search(self, query, top_k):
        return [{"id": "n1", "title": "历史经验", "score": 0.9}][:top_k]

    def add(self, doc_id, title, content, path=""):
        self.added.append((doc_id, title, content, path))


def make_ctx(tmp_path):
    return SkillContext(
        engine=FakeEngine(),
        vault=VaultStore(str(tmp_path)),
        vector=FakeVector(),
    )


def test_registry_has_six_skills():
    assert set(REGISTRY) == {"classify", "decision", "action", "review", "recall", "link"}


def test_get_skill_returns_protocol_instances():
    expected_confirm = {
        "classify": False,
        "decision": False,
        "action": True,  # 写 Vault 副作用 → confirm interrupt（B3 主管接线）
        "review": False,
        "recall": False,
        "link": False,  # 只读判断：分流决策，无副作用
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


def test_classify_skill(tmp_path):
    ctx = make_ctx(tmp_path)
    result = get_skill("classify").run(ctx, {"text": "我该选哪个方案"})
    assert result.output["label"] == "决策"
    assert result.confidence == 1.0


def test_review_skill(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.vault.create_note("决策备忘", "孤决策", "---\ntype: 决策备忘\n---")
    result = get_skill("review").run(ctx, {})
    assert len(result.output["missing"]) == 1  # read_all_notes 返回内容；孤决策缺关联 → 1 条
    assert "缺少关联问题" in result.output["missing"][0]


def test_recall_skill(tmp_path):
    ctx = make_ctx(tmp_path)
    result = get_skill("recall").run(ctx, {"task": "复盘上一个项目", "top_k": 3})
    assert result.output["results"][0]["title"] == "历史经验"


# ═══════════ M1-B2 · decision Skill（决策层：结构化追问 + 多维分析）═══════════


class FakeDecisionEngine(FakeEngine):
    def __init__(self, analysis):
        self.analysis = analysis
        self.history_calls: list[list] = []

    def analyze_decision(self, text, history=None):
        self.history_calls.append(list(history or []))
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


# ═══════════ M3-B1 · decision 消费历史参照（R1 单向依赖）═══════════


def test_decision_consumes_history_from_recall(tmp_path):
    """R1：decision 只消费 recall 传入的历史参照，自己不检索（历史结果仅展示维度）。"""
    analysis = {"question": "q", "options": [], "clarify": [], "lean": "", "confidence": 0.85}
    ctx = decision_ctx(tmp_path, analysis)
    history = [{"id": "n1", "title": "上次选B", "content": "…", "score": 0.8}]
    get_skill("decision").run(ctx, {"text": "选A还是B", "history": history})
    assert ctx.engine.history_calls == [history]  # 原样透传给 engine


def test_decision_without_history_passes_empty(tmp_path):
    """无 history 兼容（M1 旧路径 / 召回落空）：engine 收空列表而非报错。"""
    analysis = {"question": "q", "confidence": 0.85}
    ctx = decision_ctx(tmp_path, analysis)
    get_skill("decision").run(ctx, {"text": "选A还是B"})
    assert ctx.engine.history_calls == [[]]


# ═══════════ M1-B2 · action Skill（实践层：写库前 confirm）═══════════


class FakeActionEngine(FakeEngine):
    def __init__(self, draft):
        self.draft = draft

    def draft_note(self, kind, text):
        return self.draft


def action_ctx(tmp_path, draft):
    # 真 VaultStore：写入路径测真契约（ALLOWED_FOLDERS 白名单、落盘、读取）
    vault = VaultStore(str(tmp_path / "vault"))
    vector = FakeVector()
    ctx = SkillContext(engine=FakeActionEngine(draft), vault=vault, vector=vector)
    return ctx, vault, vector


MEMO_DRAFT = {
    "title": "选 A 方案",
    "content": "## 背景\n...\n## 决定\n选 A\n## 关联问题\n1. A 的成本是否可控？",
}


def test_action_unconfirmed_has_no_side_effect_and_idempotent(tmp_path):
    ctx, vault, vector = action_ctx(tmp_path, MEMO_DRAFT)
    args = {"kind": "决策备忘", "text": "决定选 A"}
    for _ in range(2):  # 重复未确认调用：零写入（幂等）
        result = get_skill("action").run(ctx, args)
        assert result.output["status"] == "needs_confirmation"
        assert result.output["title"] == "选 A 方案"  # 预览带给用户看（B3 confirm interrupt 的内容）
        assert "关联问题" in result.output["content"]
    assert vault.list_notes("决策备忘") == []
    assert vector.added == []  # 零副作用含索引：未确认不 add


def test_action_confirmed_writes_decision_memo(tmp_path):
    ctx, vault, vector = action_ctx(tmp_path, MEMO_DRAFT)
    result = get_skill("action").run(
        ctx, {"kind": "决策备忘", "text": "决定选 A", "confirmed": True}
    )
    assert result.output["status"] == "written"
    assert result.output["path"].endswith(".md")
    notes = vault.list_notes("决策备忘")
    assert len(notes) == 1
    assert "关联问题" in notes[0].read_text(encoding="utf-8")  # 闭环契约：review 扫描依赖该节
    # B5 写入即索引：确认写入后同步向量库（recall 才能召回 agent 写的卡）
    assert len(vector.added) == 1
    doc_id, title, content, path = vector.added[0]
    assert title == "选 A 方案"
    assert "关联问题" in content
    assert path.endswith(".md")


def test_action_confirmed_writes_todo_into_action_log(tmp_path):
    todo_draft = {"title": "联系供应商", "content": "## 下一步\n询价三家\n## 次日跟进\n明早 10 点"}
    ctx, vault, vector = action_ctx(tmp_path, todo_draft)
    result = get_skill("action").run(
        ctx, {"kind": "待办", "text": "要询价", "confirmed": True}
    )
    assert result.output["status"] == "written"
    notes = vault.list_notes("行动记录")  # 待办 → 行动记录（Vault 白名单目录）
    assert len(notes) == 1
    assert "次日跟进" in notes[0].read_text(encoding="utf-8")
    assert len(vector.added) == 1  # 待办写入同样索引


def test_action_unknown_kind_rejected_before_any_work(tmp_path):
    ctx, vault, vector = action_ctx(tmp_path, MEMO_DRAFT)
    with pytest.raises(ValueError):  # 入口即拒绝（未确认/已确认一致），不产出预览也不写库
        get_skill("action").run(ctx, {"kind": "乱写", "text": "x", "confirmed": True})
    assert vault.list_notes("决策备忘") == []
    assert vector.added == []


# ═══════════ M2-B1 · action Skill links 渲染（写卡自动双链的写入侧）═══════════


def test_action_confirmed_renders_links_section(tmp_path):
    ctx, vault, vector = action_ctx(tmp_path, MEMO_DRAFT)
    result = get_skill("action").run(
        ctx,
        {
            "kind": "决策备忘",
            "text": "决定选 A",
            "confirmed": True,
            "links": ["艾森豪威尔矩阵", "二八法则"],
        },
    )
    assert result.output["status"] == "written"
    body = vault.list_notes("决策备忘")[0].read_text(encoding="utf-8")
    assert _SECTION_LINK.search(body)  # 双链节存在（区别于「## 关联问题」契约节）
    assert "[[艾森豪威尔矩阵]]" in body
    assert "[[二八法则]]" in body
    # 写入即索引：向量库内容与落盘一致（渲染后的正文，含关联节）
    assert "[[艾森豪威尔矩阵]]" in vector.added[0][2]


def test_action_links_skip_existing_manual_links(tmp_path):
    draft = {
        "title": "选 A 方案",
        "content": "## 背景\n参考 [[艾森豪威尔矩阵]]\n## 决定\n选 A",
    }
    ctx, vault, vector = action_ctx(tmp_path, draft)
    get_skill("action").run(
        ctx,
        {
            "kind": "决策备忘",
            "text": "决定选 A",
            "confirmed": True,
            "links": ["艾森豪威尔矩阵", "艾森豪威尔矩阵", "二八法则"],
        },
    )
    body = vault.list_notes("决策备忘")[0].read_text(encoding="utf-8")
    assert body.count("[[艾森豪威尔矩阵]]") == 1  # 正文人工链不重复追加
    assert body.count("[[二八法则]]") == 1  # args 内重复标题也去重


def test_action_without_links_has_no_section(tmp_path):
    ctx, vault, vector = action_ctx(tmp_path, MEMO_DRAFT)
    get_skill("action").run(ctx, {"kind": "决策备忘", "text": "决定选 A", "confirmed": True})
    body = vault.list_notes("决策备忘")[0].read_text(encoding="utf-8")
    assert not _SECTION_LINK.search(body)  # 无建议链：不产生空关联节
    assert "[[" not in body  # 也没有任何 wikilink 落盘


# ═══════════ M2-B1 · link Skill（三档阈值分流 + 去重 + 人工链排除）═══════════


class FakeLinkEngine:
    """judge_link 可控 + 调用记录（"零 LLM"与"LLM 档"断言依据）。"""

    def __init__(self, judge=None):
        self.judge = judge if judge is not None else {"link_to": True, "confidence": 0.8}
        self.judge_calls: list[str] = []

    def judge_link(self, title, content, candidate):
        self.judge_calls.append(candidate.get("title", ""))
        return dict(self.judge)


def run_link(engine, title="选 A 方案", content="## 背景\n...\n## 决定\n选 A", candidates=None):
    # link 只依赖 engine（LLM 边缘判断）；候选由主管从 recall 步骤结果传入 args
    ctx = SkillContext(engine=engine, vault=None, vector=None)
    return get_skill("link").run(
        ctx, {"title": title, "content": content, "candidates": candidates or []}
    )


def cand(title, score):
    return {"id": f"c-{title}", "title": title, "content": "既有卡片内容", "score": score}


def test_link_auto_tier_links_without_llm():
    engine = FakeLinkEngine()
    result = run_link(engine, candidates=[cand("艾森豪威尔矩阵", 0.9)])
    assert result.output["links"] == ["艾森豪威尔矩阵"]
    assert result.output["pending_review"] == []
    assert result.output["judged"] == []
    assert engine.judge_calls == []  # 高分档零 LLM：阈值内直接链


def test_link_llm_tier_asks_engine_and_links_on_approve():
    engine = FakeLinkEngine(judge={"link_to": True, "confidence": 0.8})
    result = run_link(engine, candidates=[cand("成本考量", 0.8)])
    assert engine.judge_calls == ["成本考量"]
    assert result.output["links"] == ["成本考量"]
    assert result.output["judged"] == [
        {"title": "成本考量", "score": 0.8, "link_to": True, "confidence": 0.8}
    ]


def test_link_llm_tier_rejected_not_linked():
    engine = FakeLinkEngine(judge={"link_to": False, "confidence": 0.7})
    result = run_link(engine, candidates=[cand("成本考量", 0.8)])
    assert result.output["links"] == []
    assert result.output["judged"][0]["link_to"] is False


def test_link_llm_tier_invalid_verdict_defaults_no_link():
    engine = FakeLinkEngine(judge={"link_to": "yes", "confidence": 0.9})  # 非布尔
    result = run_link(engine, candidates=[cand("成本考量", 0.8)])
    assert result.output["links"] == []  # 宁可不链，不可误链


def test_link_low_tier_goes_pending_review():
    engine = FakeLinkEngine()
    result = run_link(engine, candidates=[cand("弱相关", 0.6)])
    assert result.output["links"] == []
    assert result.output["pending_review"] == [{"title": "弱相关", "score": 0.6}]
    assert engine.judge_calls == []


def test_link_dedup_same_title_keeps_highest_score():
    engine = FakeLinkEngine()
    result = run_link(engine, candidates=[cand("同名卡", 0.7), cand("同名卡", 0.9)])
    assert result.output["links"] == ["同名卡"]  # 0.9 命中 auto 档
    assert result.output["pending_review"] == []  # 0.7 的同名候选被去重，不独立分流


def test_link_excludes_manual_wikilinks_in_draft():
    engine = FakeLinkEngine()
    content = "## 背景\n已引用 [[艾森豪威尔矩阵]]\n## 决定\n选 A"
    result = run_link(engine, content=content, candidates=[cand("艾森豪威尔矩阵", 0.95)])
    assert result.output["links"] == []  # 人工显式链优先：自动链不重复建议
    assert engine.judge_calls == []


def test_link_missing_score_treated_as_low():
    engine = FakeLinkEngine()
    result = run_link(engine, candidates=[{"id": "c", "title": "无分卡", "content": "..."}])
    assert result.output["pending_review"][0]["title"] == "无分卡"
    assert result.output["links"] == []

