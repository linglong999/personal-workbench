from workbench.knowledge.vector import VectorStore


def test_add_and_search(tmp_path):
    vs = VectorStore(str(tmp_path))
    vs.add("卡片1", "艾森豪威尔矩阵", "重要且紧急，立刻做")
    vs.add("卡片2", "二八法则", "少数关键因素决定大部分结果")
    results = vs.search("优先级排序方法", top_k=2)
    assert len(results) >= 1
    assert results[0]["id"] in {"卡片1", "卡片2"}
