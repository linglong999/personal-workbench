"""Chroma 向量检索。"""
import hashlib
from chromadb import PersistentClient
from chromadb.api.types import EmbeddingFunction, Documents


class _LocalEmbeddingFunction(EmbeddingFunction):
    """无网络依赖的本地 embedding：零下载，统计式词袋向量。

    用于 Chroma 默认 ONNX 模型（all-MiniLM-L6-v2）需联网下载、网络受限时的回退。
    中文按字词 bigram 计频，向量做余弦可排序（同一话题的文档相似度更高）。
    """

    def __init__(self, dim: int = 1024):
        EmbeddingFunction.__init__(self)
        self._dim = dim

    def _tokens(self, text: str):
        # 中英统一：空白切 token + 全部 2-gram 字元，兼顾英文词与中文短语
        toks = []
        for piece in text.lower().split():
            toks.append(piece)
            toks.extend(piece[i:i + 2] for i in range(len(piece) - 1))
        return toks

    def __call__(self, input: Documents) -> list[list[float]]:
        results = []
        for doc in input:
            vec = {}
            for tok in self._tokens(doc):
                idx = int.from_bytes(hashlib.sha256(tok.encode("utf-8")).digest()[:4], "big") % self._dim
                vec[idx] = vec.get(idx, 0.0) + 1.0
            if not vec:
                results.append([0.0] * self._dim)
                continue
            norm = sum(v * v for v in vec.values()) ** 0.5
            out = [0.0] * self._dim
            for k, v in vec.items():
                out[k] = v / norm
            results.append(out)
        return results


def _default_embedding():
    # 默认使用本地哈希 embedding：零网络依赖，离线即测即用。
    # 对应 README「已知限制」的网络受限降级约定；如需更高质量语义检索，
    # 可改为 ONNXMiniLM_L6_V2（需首次联网下载约 79MB 模型）。
    return _LocalEmbeddingFunction()


class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = PersistentClient(path=persist_dir)
        self.ef = _default_embedding()
        self.collection = self.client.get_or_create_collection(
            name="knowledge", embedding_function=self.ef
        )

    def add(self, doc_id: str, title: str, content: str):
        text = f"{title}\n{content}"
        self.collection.upsert(ids=[doc_id], documents=[text], metadatas=[{"title": title}])

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        res = self.collection.query(query_texts=[query], n_results=top_k)
        docs = res.get("documents", [[]])[0] or []
        ids = res.get("ids", [[]])[0] or []
        metas = res.get("metadatas", [[]])[0] or []
        metas = metas or [{}] * len(ids)
        return [{"id": i, "title": m.get("title", ""), "content": d} for i, d, m in zip(ids, docs, metas)]