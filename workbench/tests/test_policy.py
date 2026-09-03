"""M3-B1 policy 路由测试：决策链路 recall(history)→decision(history) 与 recall 三档用途。

不跑 Orchestrator，手搭 RunView 直问 RulePolicy——路由顺序的精确断言
（编排后行为与事件链归 test_orchestrator / golden case）。
"""

from workbench.ai.policy import Finish, RulePolicy, RunSkill, RunView, Step

CLASSIFIED_DECISION = Step("classify", {"text": "选A还是B"}, {"label": "决策"})
HIGH_CONF = {
    "question": "选A还是B",
    "dimensions": ["成本"],
    "options": [{"name": "A", "pros": "快", "cons": "糙"}],
    "clarify": [],
    "lean": "倾向A",
    "confidence": 0.85,
}
MEMO_DRAFT = {"title": "选A方案", "content": "## 决定\n选A", "status": "needs_confirmation"}
HISTORY_RECALL = Step(
    "recall",
    {"task": "选A还是B", "top_k": 3, "purpose": "history"},
    {"results": [{"id": "n1", "title": "上次选B", "score": 0.8}]},
)


def view(text, steps):
    return RunView(text, list(steps), [])


# ═══════════ 决策链路：recall(history) → decision(history) ═══════════


def test_decision_flow_recalls_history_first():
    instr = RulePolicy().next_instruction(view("选A还是B", [CLASSIFIED_DECISION]))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "recall"
    assert instr.args["purpose"] == "history"  # 历史参照档（不是候选/收尾档）
    assert instr.args["task"] == "选A还是B"


def test_decision_flow_passes_recall_results_as_history():
    instr = RulePolicy().next_instruction(view("选A还是B", [CLASSIFIED_DECISION, HISTORY_RECALL]))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "decision"
    assert instr.args["history"] == HISTORY_RECALL.result["results"]  # 参照注入


def test_decision_flow_empty_history_still_decides():
    empty = Step("recall", {"task": "选A还是B", "purpose": "history"}, {"results": []})
    instr = RulePolicy().next_instruction(view("选A还是B", [CLASSIFIED_DECISION, empty]))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "decision"
    assert instr.args["history"] == []  # 召回落空不卡流程


# ═══════════ recall 三档用途互不串档 ═══════════


def test_history_recall_not_confused_with_candidate_recall():
    """决策流的历史召回不得被 confirm 管线误认为双链候选召回。"""
    steps = [
        CLASSIFIED_DECISION,
        HISTORY_RECALL,
        Step("decision", {"text": "选A还是B"}, HIGH_CONF),
        Step("action", {"kind": "决策备忘", "text": "选A还是B"}, MEMO_DRAFT),
    ]
    instr = RulePolicy().next_instruction(view("选A还是B", steps))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "recall"
    assert instr.args["purpose"] == "candidates"  # 草稿就绪要的是双链候选，不复用历史召回
    assert instr.args["top_k"] == 20


def test_candidate_recall_then_link():
    steps = [
        CLASSIFIED_DECISION,
        HISTORY_RECALL,
        Step("decision", {"text": "选A还是B"}, HIGH_CONF),
        Step("action", {"kind": "决策备忘", "text": "选A还是B"}, MEMO_DRAFT),
        Step("recall", {"task": "草稿", "top_k": 20, "purpose": "candidates"}, {"results": []}),
    ]
    instr = RulePolicy().next_instruction(view("选A还是B", steps))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "link"
    assert instr.args["candidates"] == []


def test_practice_flow_has_no_history_recall():
    steps = [Step("classify", {"text": "要询价"}, {"label": "实践"})]
    instr = RulePolicy().next_instruction(view("要询价", steps))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "action"  # 实践直接起草：历史参照是决策链专属


def test_finish_recall_uses_finish_purpose():
    steps = [
        Step("classify", {"text": "复盘一下"}, {"label": "复盘"}),
        Step("review", {}, {"missing": []}),
    ]
    instr = RulePolicy().next_instruction(view("复盘一下", steps))
    assert isinstance(instr, RunSkill)
    assert instr.skill == "recall"
    assert instr.args["purpose"] == "finish"

    steps.append(Step("recall", {"task": "复盘一下", "top_k": 3, "purpose": "finish"}, {"results": []}))
    instr = RulePolicy().next_instruction(view("复盘一下", steps))
    assert isinstance(instr, Finish)
