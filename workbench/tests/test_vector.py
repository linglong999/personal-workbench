from workbench.knowledge.vector import VectorStore


def test_add_and_search(tmp_path):
    vs = VectorStore(str(tmp_path))
    vs.add("卡片1", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vs.add("卡片2", "二八法则", "少数关键因素决定大部分结果")
    results = vs.search("优先级排序方法", top_k=2)
    assert len(results) >= 1
    assert results[0]["id"] in {"卡片1", "卡片2"}


def test_search_returns_score_sorted_desc(tmp_path):
    """M2-B1：search 返回 score（1 - cosine 距离），按相似度降序——link 三档分流的前提。"""
    vs = VectorStore(str(tmp_path))
    vs.add("卡片1", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vs.add("卡片2", "二八法则", "少数关键因素决定大部分结果")
    results = vs.search("优先级排序方法", top_k=2)
    scores = [r["score"] for r in results]
    assert all(isinstance(s, float) for s in scores)
    assert scores == sorted(scores, reverse=True)  # 降序：最相关在前


def test_search_exact_match_scores_high(tmp_path):
    """本地哈希 embedding 的量纲低于语义模型（标题命中约 0.4），断言用相对排序不绑量纲：
    三档阈值按语义 embedding 设计，本地回退时高分档难命中 → 安全降级 pending_review。"""
    vs = VectorStore(str(tmp_path))
    vs.add("卡片1", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vs.add("卡片2", "二八法则", "少数关键因素决定大部分结果")
    results = vs.search("艾森豪威尔矩阵", top_k=2)
    assert results[0]["id"] == "卡片1"
    assert results[0]["score"] > 0  # 命中标题给出正分（可判档）
    assert results[0]["score"] > results[1]["score"]  # 相关卡分数严格高于无关卡


def test_search_missing_distances_defaults_to_zero_score(tmp_path, monkeypatch):
    """review 修正：距离缺失（API 异常形态）时兜底最大距离 → score=0 进最低档——
    若兜底 0.0 距离会把异常结果顶到 auto 档自动建链，违背"宁可不链，不可误链"。"""
    vs = VectorStore(str(tmp_path))

    def fake_query(query_texts, n_results):
        return {
            "documents": [["既有卡片内容"]],
            "ids": [["卡片1"]],
            "metadatas": [[{"title": "卡片1", "path": ""}]],
        }  # 无 distances

    monkeypatch.setattr(vs.collection, "query", fake_query)
    results = vs.search("任意查询", top_k=1)
    assert results[0]["title"] == "卡片1"
    assert results[0]["score"] == 0.0  # 兜底最低分：异常距离不进 auto 档
