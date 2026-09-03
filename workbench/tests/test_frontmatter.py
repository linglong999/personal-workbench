"""M3-B2 · frontmatter 编/解码测试：两栏 enum + 宽容读回。

对应 Step 0 检查表：1（顶部一组 ---、正文 --- 不截断、丢 meta 不丢正文）、
2（enum 英文裸值/特殊值引号/ISO 日期）、4（enum_or_unknown 宁缺毋猜）、
7（存量宽容：无 frontmatter / 缺字段缺省）。
"""

import re

from workbench.ai.frontmatter import (
    OUTCOME_ENUM,
    QUALITY_ENUM,
    encode,
    enum_or_unknown,
    parse,
)

FULL_META = {
    "type": "决策",
    "date": "2026-09-03",
    "decision": "选 A：成本低交付快",
    "context": "两个供应商比价",
    "criteria": "成本, 交付速度",
    "expected_outcome": "两周内交付",
    "actual_outcome": "unknown",
    "result_quality": "unknown",
    "applicability": "小团队采购场景",
}


# ═══════════ encode：dict → frontmatter 文本块 ═══════════


def test_encode_parse_roundtrip():
    """编码后再解析：meta 逐字段还原（含中文、逗号、全角冒号值）。"""
    meta, body = parse(encode(FULL_META) + "\n正文")
    assert meta == FULL_META
    assert body == "正文"


def test_encode_quotes_special_values_keeps_enum_bare():
    """check 2：含中文/冒号/逗号的值加引号（YAML 安全）；enum 与日期裸值。"""
    text = encode(FULL_META)
    assert 'decision: "选 A：成本低交付快"' in text  # 全角冒号+中文 → 引号
    assert 'criteria: "成本, 交付速度"' in text  # 逗号 → 引号
    assert "actual_outcome: unknown" in text  # enum 英文裸值
    assert "result_quality: unknown" in text
    assert "date: 2026-09-03" in text  # ISO 日期裸值


def test_encode_empty_meta_returns_empty_string():
    assert encode({}) == ""


def test_encode_skips_empty_values():
    """空值栏不输出（无信息量），有值栏保留。"""
    text = encode({"type": "决策", "decision": "", "context": "背景"})
    assert "decision" not in text
    assert "context: 背景" in text or 'context: "背景"' in text


# ═══════════ parse：宽容读回（存量卡 + 手改笔误）═══════════


def test_parse_body_separators_not_truncated():
    """check 1：正文里的 ---（Markdown 分隔线/代码块）不得截断正文。"""
    body_text = "第一段\n\n---\n\n第二段（分隔线后）"
    meta, body = parse(encode({"type": "决策"}) + "\n" + body_text)
    assert meta == {"type": "决策"}
    assert body == body_text  # 正文中的 --- 原样保留


def test_parse_without_closing_fence_drops_meta_keeps_body():
    """check 1：只有开头 --- 无闭合 → 丢 meta 不丢正文（整个原文都是 body）。"""
    text = "---\ntype: 决策\n正文没有闭合围栏"
    meta, body = parse(text)
    assert meta == {}
    assert body == text  # 一字不丢


def test_parse_plain_text_returns_as_is():
    """check 7：存量旧卡无 frontmatter → 原样返回，meta 空。"""
    text = "## 背景\n老卡正文"
    meta, body = parse(text)
    assert meta == {}
    assert body == text


def test_parse_lenient_skips_malformed_lines():
    """frontmatter 块内烂行（无冒号/手改笔误）跳过，好行保留。"""
    text = "---\ntype: 决策\n这行没有冒号\ndate: 2026-09-03\n---\n正文"
    meta, body = parse(text)
    assert meta == {"type": "决策", "date": "2026-09-03"}
    assert body == "正文"


def test_parse_legacy_missing_enum_fields_default_unknown():
    """check 7：存量卡 frontmatter 缺 enum 字段 → 读回缺键，消费侧缺省 unknown。"""
    text = "---\ntype: 决策\ndate: 2026-01-01\n---\n老决策正文"
    meta, body = parse(text)
    assert "actual_outcome" not in meta
    assert enum_or_unknown(meta.get("actual_outcome"), OUTCOME_ENUM) == "unknown"
    assert enum_or_unknown(meta.get("result_quality"), QUALITY_ENUM) == "unknown"


# ═══════════ enum_or_unknown：宁缺毋猜（check 4）═══════════


def test_enum_or_unknown_strict():
    """合法值透传；非法（含中文/大写/自由文本）与缺失一律 unknown，不硬猜。"""
    assert enum_or_unknown("success", OUTCOME_ENUM) == "success"
    assert enum_or_unknown("good", QUALITY_ENUM) == "good"
    assert enum_or_unknown("成功", OUTCOME_ENUM) == "unknown"  # 中文不入 enum
    assert enum_or_unknown("SUCCESS", OUTCOME_ENUM) == "unknown"  # 大小写敏感
    assert enum_or_unknown("成功了", QUALITY_ENUM) == "unknown"  # 不因词面硬映射
    assert enum_or_unknown(None, OUTCOME_ENUM) == "unknown"
    assert enum_or_unknown("", OUTCOME_ENUM) == "unknown"


def test_outcome_and_quality_enum_values_match_decision_8():
    """决策 8：actual_outcome ∈ success/failure/inconclusive/unknown；
    result_quality ∈ good/medium/poor/unknown。"""
    assert OUTCOME_ENUM == ("success", "failure", "inconclusive", "unknown")
    assert QUALITY_ENUM == ("good", "medium", "poor", "unknown")


def test_encode_date_iso_format():
    """check 2：日期严格 ISO 8601（encode 透传，draft_note 侧生成）。"""
    text = encode({"date": "2026-09-03"})
    assert re.search(r"date: \d{4}-\d{2}-\d{2}", text)
