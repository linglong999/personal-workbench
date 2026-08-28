"""重建向量索引：把 Vault 知识卡片重新入库，元数据补上文件路径。

背景：e2e_real.py 首次索引时未存 path，导致前端检索结果无法回跳 Obsidian
原文。本脚本按相同 id（card-{标题}）upsert，不产生重复条目。
之后的新笔记由 create_note 写入时自动带路径，无需再跑本脚本。
"""
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(Path.cwd() / "src"))

from workbench.config import load_config
from workbench.knowledge.vault import VaultStore
from workbench.knowledge.vector import VectorStore


def main():
    cfg = load_config()
    vault = VaultStore(cfg.vault_path)
    vector = VectorStore(cfg.chroma_dir)
    n = 0
    for p in vault.list_notes("知识卡片"):
        content = p.read_text(encoding="utf-8", errors="ignore")
        vector.add(f"card-{p.stem}", p.stem, content, path=str(p))
        n += 1
    print(f"reindexed {n} cards (with path metadata) -> {cfg.chroma_dir}")


if __name__ == "__main__":
    main()
