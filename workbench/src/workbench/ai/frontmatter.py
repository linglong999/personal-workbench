"""决策备忘 frontmatter 编/解码（M3-B2，M3-A 结构）。

两栏 enum（决策 8）：actual_outcome ∈ success/failure/inconclusive/unknown、
result_quality ∈ good/medium/poor/unknown——中文解释放 *_note，不进枚举字段。
宽容读回（check 1/7）：只认文件顶部一组 `---`；正文里的 `---` 不截断；
解析失败丢 meta 不丢正文；存量卡缺字段缺省（配合 enum_or_unknown）。
编码不引 YAML 依赖：键值行 + 特殊值 JSON 引号（合法 YAML 双引号标量）。
"""

import json
import re

OUTCOME_ENUM = ("success", "failure", "inconclusive", "unknown")
QUALITY_ENUM = ("good", "medium", "poor", "unknown")

FENCE = "---"
# 裸值白名单：纯 ASCII 字母数字与 . / _ 空格 连字符（enum、ISO 日期、英文短语）
_BARE_VALUE = re.compile(r"^[A-Za-z0-9_./ -]*$")


def _format_value(value) -> str:
    s = str(value)
    return s if _BARE_VALUE.match(s) else json.dumps(s, ensure_ascii=False)


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            v = json.loads(s)
            return v if isinstance(v, str) else s
        except ValueError:
            return s
    return s


def encode(meta: dict) -> str:
    """dict → `---` 包裹的 frontmatter 文本块（无尾换行）。空 meta / 空值栏返回空串。"""
    lines = [f"{k}: {_format_value(v)}" for k, v in meta.items() if v not in (None, "")]
    if not lines:
        return ""
    return "\n".join([FENCE, *lines, FENCE])


def parse(text: str) -> tuple[dict, str]:
    """宽容读回 (meta, body)。

    首行非 `---` → 无 meta；无闭合 `---` → 丢 meta 保正文（整个原文都是 body）；
    块内烂行（无冒号）跳过；闭合之后的全部内容（含后续 `---`）原样为 body。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != FENCE:
        return {}, text
    meta: dict = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == FENCE:
            return meta, "\n".join(lines[i + 1 :])
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        meta[key.strip()] = _unquote(raw.strip())
    return {}, text


def enum_or_unknown(value, allowed) -> str:
    """enum 规范化（check 4 宁缺毋猜）：非法/缺失一律 unknown，不按词面硬猜。"""
    s = str(value).strip() if value is not None else ""
    return s if s in allowed else "unknown"
