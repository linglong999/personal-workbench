import json
import re

from workbench.ai.engine import AIEngine
from workbench.ai.frontmatter import parse


class FakeLLM:
    def complete(self, system, user, skill=""):
        return "分类打标: 决策与策略"


class StubLLM:
    """返回固定应答——测 engine 的 JSON 解析边界（LLM 是外部系统边界）。"""

    def __init__(self, response):
        self.response = response

    def complete(self, system, user, skill=""):
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
    """记录 system/user prompt——断言喂料边界与 prompt 措辞（judge_link / analyze_decision）。"""

    def __init__(self, response):
        self.response = response
        self.user = ""
        self.system = ""

    def complete(self, system, user, skill=""):
        self.user = user
        self.system = system
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


# ═══════════ M3-B1 · analyze_decision 历史参照注入（R1 只消费 + 反结果偏误）═══════════

HISTORY = [
    {"id": "n1", "title": "上次选B的决策", "content": "很" * 600, "score": 0.82},
    {"id": "n2", "title": "外包还是自研", "content": "贵" * 600, "score": 0.76},
]


def test_analyze_decision_history_injects_bounded_summary_not_full_text():
    """M3-B：参照注入为结构化摘要（标题+200字截断+score），非全文——
    成本上界，与 judge_link 同款喂料边界；按相似度递减保序注入。"""
    llm = PromptCaptureLLM(DECISION_JSON)
    engine = AIEngine(llm)
    engine.analyze_decision("先做哪个", HISTORY)
    assert "上次选B的决策" in llm.user  # 标题进 prompt
    assert "0.82" in llm.user  # score 进 prompt（展示维度，不作排序依据）
    assert llm.user.index("上次选B的决策") < llm.user.index("外包还是自研")  # 保序：相似度递减
    assert "很" * 201 not in llm.user  # 历史卡全文不进 prompt（截断为摘要）
    assert "贵" * 201 not in llm.user


def test_analyze_decision_without_history_no_block():
    """无历史参照（M1 旧路径 / 召回落空）：user prompt 就是原文，不产生空参照块。"""
    llm = PromptCaptureLLM(DECISION_JSON)
    engine = AIEngine(llm)
    engine.analyze_decision("先做哪个")
    assert llm.user == "先做哪个"
    assert "历史参照" not in llm.user


def test_analyze_decision_prompt_anti_outcome_bias():
    """反结果偏误（决策 5/6）：prompt 指令式区分决策过程质量与结果好坏。"""
    llm = PromptCaptureLLM(DECISION_JSON)
    engine = AIEngine(llm)
    engine.analyze_decision("先做哪个", HISTORY)
    assert "决策过程" in llm.system  # 过程质量与结果好坏分开评估
    assert "运气" in llm.system  # 结果好可能只是运气
    assert "未知" in llm.system  # 结果未知的参照不强行判断好坏


# ═══════════ M4-B1 · skill 归因显式贯穿（决策 10：不用 contextvars）═══════════


class SkillCaptureLLM:
    def __init__(self, response):
        self.response = response
        self.skills = []

    def complete(self, system, user, skill=""):
        self.skills.append(skill)
        return self.response


def test_engine_passes_skill_attribution_to_llm():
    """engine 各方法显式传 skill 名 → LLMClient → record_llm 落表（用量归因）。"""
    llm = SkillCaptureLLM(DRAFT_JSON)
    engine = AIEngine(llm)
    engine.classify("要询价")
    engine.analyze_decision("选A还是B")
    engine.draft_note("待办", "要询价")
    engine.judge_link("标题", "内容", {"title": "t", "content": "c", "score": 0.9})
    assert llm.skills == ["classify", "decision", "action", "link"]  # 与 Skill 名对齐


def test_analyze_decision_history_view_default_on_shape_miss():
    # 输出契约扩 history_view：残缺 JSON 按字段兜底，不 KeyError
    engine = AIEngine(StubLLM('{"confidence": 0.9}'))
    analysis = engine.analyze_decision("先做哪个", HISTORY)
    assert analysis["history_view"] == ""


# ═══════════ M3-B2 · draft_note 决策备忘两栏 enum frontmatter ═══════════

DRAFT_META_JSON = json.dumps(
    {
        "title": "选 A 方案",
        "content": "## 背景\n…\n## 决定\n选 A\n## 关联问题\n1. 成本？",
        "meta": {
            "decision": "选 A：成本低",
            "context": "两个供应商比价",
            "criteria": "成本, 交付速度",
            "expected_outcome": "两周内交付",
            "applicability": "小团队采购",
        },
    },
    ensure_ascii=False,
)


def test_draft_note_decision_memo_frontmatter_two_columns():
    """决策备忘 content 以 frontmatter 开头：type/date + LLM 自然语言栏 + 两栏 enum。"""
    engine = AIEngine(StubLLM(DRAFT_META_JSON))
    draft = engine.draft_note("决策备忘", "选A还是B")
    meta, body = parse(draft["content"])
    assert meta["type"] == "决策"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"])  # ISO 8601
    assert meta["actual_outcome"] == "unknown"  # 两栏 enum（决策 8）
    assert meta["result_quality"] == "unknown"
    assert meta["decision"] == "选 A：成本低"  # LLM 自然语言栏透传
    assert meta["criteria"] == "成本, 交付速度"
    assert "关联问题" in body  # 正文三节保留，闭环契约不破坏


def test_draft_note_todo_without_frontmatter():
    """待办不加 frontmatter（强 schema 只强决策备忘）。"""
    todo_json = json.dumps(
        {"title": "询价", "content": "## 下一步\n询价\n## 次日跟进\n明早10点"}, ensure_ascii=False
    )
    engine = AIEngine(StubLLM(todo_json))
    draft = engine.draft_note("待办", "要询价")
    assert not draft["content"].startswith("---")
    assert "actual_outcome" not in draft["content"]


def test_draft_note_enum_columns_forced_unknown_despite_llm_pollution():
    """check 4 宁缺毋猜：LLM 试图给出结果/质量（新决策不可能有）→ 代码强制 unknown。"""
    polluted = json.dumps(
        {
            "title": "选 A 方案",
            "content": "## 决定\n选 A",
            "meta": {
                "decision": "选 A",
                "actual_outcome": "success",
                "result_quality": "好",
            },
        },
        ensure_ascii=False,
    )
    engine = AIEngine(StubLLM(polluted))
    draft = engine.draft_note("决策备忘", "选A还是B")
    meta, _ = parse(draft["content"])
    assert meta["actual_outcome"] == "unknown"  # 两栏由代码硬编码，LLM 不参与
    assert meta["result_quality"] == "unknown"


def test_draft_note_meta_missing_still_minimal_frontmatter():
    """LLM 残缺（无 meta 键）：骨架仍全（type/date/两栏 unknown），自然语言栏缺省不出现。"""
    engine = AIEngine(StubLLM(DRAFT_JSON))
    draft = engine.draft_note("决策备忘", "选A还是B")
    meta, body = parse(draft["content"])
    assert meta["type"] == "决策"
    assert meta["actual_outcome"] == "unknown"
    assert meta["result_quality"] == "unknown"
    assert "decision" not in meta  # 缺省栏不出现（宁缺毋猜）
    assert "关联问题" in body


def test_draft_note_bad_json_decision_memo_keeps_skeleton():
    """LLM 抽风（非法 JSON）：决策备忘仍带骨架 frontmatter，原文兜底进正文不丢。"""
    engine = AIEngine(StubLLM("模型抽风了"))
    draft = engine.draft_note("决策备忘", "选A还是B")
    meta, body = parse(draft["content"])
    assert meta["actual_outcome"] == "unknown"
    assert meta["result_quality"] == "unknown"
    assert body == "选A还是B"  # 原文兜底，丢 meta 不丢正文
