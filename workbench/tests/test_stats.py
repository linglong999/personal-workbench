"""M4-B2 stats 聚合模块测试：分布/双链/趋势/chroma 计数（纯函数，真组件 tmp 落盘）。

口径锁定（计划文档决策 17/19/20）：distribution 含全部 6 白名单目录含零值、
count 降序同数按目录名稳定序；双链 = 唯一 (source, target) 边（剥别名/标题/.md、
嵌入计入、同文件重复去重）；趋势只认文件名日期前缀，无前缀文件计总数不计趋势。
"""

from datetime import date, timedelta

from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore
from workbench.stats import knowledge_stats


def _mk(tmp_path):
    return VaultStore(str(tmp_path / "vault")), VectorStore(str(tmp_path / "chroma"))


def _note(vault, folder: str, filename: str, content: str = "正文") -> None:
    """直接落盘指定文件名（create_note 只写今天日期前缀，历史日需手动造）。"""
    d = vault.root / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(content, encoding="utf-8")


def test_distribution_all_folders_zero_filled_and_sorted(tmp_path):
    """决策 19：6 目录含零值全出现，count 降序，同数（零值组）按目录名稳定序。"""
    vault, vector = _mk(tmp_path)
    vault.create_note("知识卡片", "卡A", "a")
    vault.create_note("知识卡片", "卡B", "b")
    vault.create_note("决策备忘", "决策A", "c")
    s = knowledge_stats(vault, vector)
    assert [d["name"] for d in s["distribution"]] == [
        "知识卡片",  # 2
        "决策备忘",  # 1
        "复盘沉淀",  # 0，零值组按 unicode 目录名稳定序
        "愿景与原则",
        "行动记录",
        "问题整理",
    ]
    assert s["total_notes"] == 3


def test_links_unique_edges_with_variants(tmp_path):
    """决策 17：唯一边口径——同文件重复计 1、剥 |别名 / #标题 / .md、嵌入计入、空链跳过。"""
    vault, vector = _mk(tmp_path)
    _note(
        vault,
        "知识卡片",
        "2026-09-03-甲.md",
        "[[乙]] [[乙]] [[丙|别名]] [[丁#标题]] ![[戊]] [[己.md]] [[]]",
    )
    _note(vault, "行动记录", "2026-09-03-庚.md", "见 [[乙]] 和 [[甲]]")
    # 甲→乙(去重1) 丙 丁 戊 己 = 5 边；庚→乙 庚→甲 = 2 边；[[]] 空链不计
    assert knowledge_stats(vault, vector)["links"] == 7


def test_knowledge_trend_from_filename_prefix(tmp_path):
    """决策 20：趋势按文件名日期前缀，缺失日补零，无前缀文件计总数不计趋势。"""
    vault, vector = _mk(tmp_path)
    today = date.today()
    y = (today - timedelta(days=1)).isoformat()
    _note(vault, "知识卡片", f"{today.isoformat()}-卡1.md")
    _note(vault, "知识卡片", f"{today.isoformat()}-卡2.md")
    _note(vault, "决策备忘", f"{y}-决策1.md")
    _note(vault, "问题整理", "无日期前缀的旧卡.md")  # 存量宽容：计总数不计趋势
    s = knowledge_stats(vault, vector, days=7)
    trend = s["trend"]
    assert len(trend) == 7  # 补零：起止日内每天都有点
    assert trend[-1] == {"date": today.isoformat(), "value": 2}  # 含今日
    assert trend[-2] == {"date": y, "value": 1}
    assert trend[0]["value"] == 0
    assert s["total_notes"] == 4


def test_chroma_count_passthrough(tmp_path):
    """决策 18：chroma_count = collection.count() 直封装，VectorStore.count() 可直调。"""
    vault, vector = _mk(tmp_path)
    assert vector.count() == 0
    assert knowledge_stats(vault, vector)["chroma_count"] == 0
    vector.add("doc1", "标题1", "内容1")
    vector.add("doc2", "标题2", "内容2")
    assert knowledge_stats(vault, vector)["chroma_count"] == 2
