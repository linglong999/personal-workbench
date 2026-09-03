import json

from workbench.ai.engine import AIEngine


class FakeLLM:
    def complete(self, system, user):
        return "分类打标: 决策与策略"


class StubLLM:
    """返回固定应答——测 engine 的 JSON 解析边界（LLM 是外部系统边界）。"""

    def __init__(self, response):
        self.response = response

    def complete(self, system, user):
        return self.response


def test_classify():
    engine = AIEngine(FakeLLM())
    result = engine.classify("我该选哪个方案")
    assert "决策" in result


# ═══════════ M1-B2 · engine 决策层/实践层方法（JSON 边界）═══════════

DECISION_JSON = json.dumps(
    {
        "question": "先做哪个功能",
        "dimensions": ["成本"],
        "options": [{"name": "A", "pros": "快", "cons": "糙"}],
        "clarify": [],
        "lean": "倾向 A",
        "confidence": 0.8,
    },
    ensure_ascii=False,
)

DRAFT_JSON = json.dumps(
    {"title": "选 A 方案", "content": "## 背景\n…\n## 决定\n选 A\n## 关联问题\n1. 成本？"},
    ensure_ascii=False,
)


def test_analyze_decision_parses_json():
    engine = AIEngine(StubLLM(DECISION_JSON))
    analysis = engine.analyze_decision("先做哪个功能")
    assert analysis["question"] == "先做哪个功能"
    assert analysis["confidence"] == 0.8


def test_analyze_decision_falls_back_on_bad_json():
    engine = AIEngine(StubLLM("不是 JSON，模型抽风了"))
    analysis = engine.analyze_decision("先做哪个")
    assert analysis["options"] == []
    assert analysis["confidence"] == 0.0  # 回退即低置信 → 上游 needs_judgement
    assert "不是 JSON" in analysis["question"]  # 原文兜底进 question，不丢信息


def test_analyze_decision_falls_back_on_non_dict():
    engine = AIEngine(StubLLM('["数组不是对象"]'))
    analysis = engine.analyze_decision("先做哪个")
    assert analysis["confidence"] == 0.0
    assert analysis["options"] == []


def test_analyze_decision_defaults_on_shape_miss():
    # 合法 JSON 但字段残缺（LLM 常见失败模式）：按字段兜底，不 KeyError
    engine = AIEngine(StubLLM('{"confidence": 0.9}'))
    analysis = engine.analyze_decision("先做哪个")
    assert analysis["confidence"] == 0.9  # 已有字段透传
    assert analysis["options"] == []  # 残缺字段给默认
    assert analysis["clarify"] == []


def test_draft_note_parses_json():
    engine = AIEngine(StubLLM(DRAFT_JSON))
    draft = engine.draft_note("决策备忘", "决定选 A")
    assert draft["title"] == "选 A 方案"
    assert "关联问题" in draft["content"]


def test_draft_note_falls_back_on_bad_json():
    engine = AIEngine(StubLLM("{oops"))
    draft = engine.draft_note("待办", "要询价")
    assert draft["title"].startswith("要询价")  # 回退：原文前缀作标题、原文作正文
    assert draft["content"] == "要询价"


def test_draft_note_defaults_on_shape_miss():
    engine = AIEngine(StubLLM('{"title": "只有标题"}'))
    draft = engine.draft_note("待办", "要询价")
    assert draft["title"] == "只有标题"
    assert draft["content"] == "要询价"  # 残缺 content 给原文兜底


def test_check_closed_loop_rules():
    engine = AIEngine(FakeLLM())
    problems = engine.check_closed_loop(["含关联问题的备忘", "孤决策"])
    assert problems == ["孤决策 缺少关联问题"]


# ═══════════ M2-B1 · engine.judge_link（关联判断，JSON 边界三态）═══════════

JUDGE_CANDIDATE = {"id": "c1", "title": "成本考量", "content": "各方案成本对比", "score": 0.8}


def test_judge_link_parses_json():
    engine = AIEngine(StubLLM(json.dumps({"link_to": True, "confidence": 0.8})))
    verdict = engine.judge_link("选 A 方案", "## 决定\n选 A", JUDGE_CANDIDATE)
    assert verdict == {"link_to": True, "confidence": 0.8}


def test_judge_link_bad_json_defaults_no_link():
    engine = AIEngine(StubLLM("模型抽风了，不是 JSON"))
    verdict = engine.judge_link("选 A 方案", "## 决定\n选 A", JUDGE_CANDIDATE)
    assert verdict["link_to"] is False
    assert verdict["confidence"] == 0.0


def test_judge_link_missing_field_defaults_no_link():
    engine = AIEngine(StubLLM('{"confidence": 0.9}'))  # 残缺：缺 link_to
    verdict = engine.judge_link("选 A 方案", "## 决定\n选 A", JUDGE_CANDIDATE)
    assert verdict["link_to"] is False


def test_judge_link_non_bool_link_to_defaults_no_link():
    engine = AIEngine(StubLLM('{"link_to": "yes", "confidence": 0.9}'))  # 类型残缺
    verdict = engine.judge_link("选 A 方案", "## 决定\n选 A", JUDGE_CANDIDATE)
    assert verdict["link_to"] is False  # 宁可不链，不可误链


class PromptCaptureLLM:
    """记录 user prompt——断言 judge_link 的喂料边界（标题+摘要+score，不喂全文）。"""

    def __init__(self, response):
        self.response = response
        self.user = ""

    def complete(self, system, user):
        self.user = user
        return self.response


def test_judge_link_feeds_bounded_summary_not_full_text():
    """M2-A 管线（review 补）：边缘档仅喂 标题+摘要(200字截断)+score——
    成本上界（长文不放大 token）+ 近全卡会误判同名词卡（业界核实）。"""
    llm = PromptCaptureLLM('{"link_to": false, "confidence": 0.5}')
    engine = AIEngine(llm)
    engine.judge_link("选 A 方案", "很" * 600, {"title": "成本考量", "content": "贵" * 600, "score": 0.8})
    assert "选 A 方案" in llm.user  # 标题进 prompt
    assert "0.8" in llm.user  # score 进 prompt 供 LLM 校准
    assert "很" * 201 not in llm.user  # 新笔记全文不进 prompt（截断为摘要）
    assert "贵" * 201 not in llm.user  # 候选全文不进 prompt
