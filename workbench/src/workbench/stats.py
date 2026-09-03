"""知识存量统计聚合（M4-B2）：目录分布 + 双链唯一边数 + 文件名前缀趋势 + chroma 计数。

纯函数模块：收 VaultStore/VectorStore 实例，无全局状态；bridge /api/stats 只做
参数解析与响应组装（决策 21）。口径见计划文档：双链 = 唯一 (source, target) 边
（决策 17，剥别名/标题/.md，嵌入计入）；distribution 含全部 6 目录含零值、
count 降序同数按目录名稳定序（决策 19）；趋势只认文件名日期前缀
（indexer 同款正则），无前缀文件计总数不计趋势（决策 20，存量宽容）。
"""

import re
from datetime import date, timedelta

from workbench.knowledge.vault import ALLOWED_FOLDERS, VaultStore
from workbench.knowledge.vector import VectorStore

_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


def _norm_target(raw: str) -> str:
    """规范化 wikilink target：剥 |别名、剥 #标题/块引用、剥 .md 后缀。"""
    return raw.split("|")[0].split("#")[0].strip().removesuffix(".md")


def count_links(vault: VaultStore) -> int:
    """唯一 (source, target) 边数：Obsidian 图谱边语义，同文件重复链同一目标计 1。"""
    edges: set[tuple[str, str]] = set()
    for folder in ALLOWED_FOLDERS:
        for p in vault.list_notes(folder):
            for m in _WIKILINK.finditer(p.read_text(encoding="utf-8")):
                target = _norm_target(m.group(1))
                if target:
                    edges.add((p.stem, target))
    return len(edges)


def knowledge_stats(vault: VaultStore, vector: VectorStore, days: int = 7) -> dict:
    counts = {f: len(vault.list_notes(f)) for f in ALLOWED_FOLDERS}
    today = date.today()
    wanted = [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    per_day = dict.fromkeys(wanted, 0)
    for folder in ALLOWED_FOLDERS:
        for p in vault.list_notes(folder):
            m = _DATE_PREFIX.match(p.stem)
            if m and m.group(1) in per_day:
                per_day[m.group(1)] += 1
    distribution = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "total_notes": sum(counts.values()),
        "distribution": [{"name": f, "count": c} for f, c in distribution],
        "links": count_links(vault),
        "chroma_count": vector.count(),
        "trend": [{"date": d, "value": v} for d, v in per_day.items()],
    }
