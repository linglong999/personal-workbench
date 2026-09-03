"""hash 增量索引（M2-B2）：Vault 白名单目录 → 向量库，content_hash 命中即跳过。

用途：首次初始化全量入库 + 用户在 Obsidian 手动改卡后的增量重算（只重算变更卡，
不全文重扫）。doc_id 与写卡路径同款 `note-{stem}`——sync 与 action/create_note/MCP
互认，同一张卡不产重复条目。upsert 语义**不处理删除/改名**（最小版约定：改名产生
新条目、旧条目留全量重建清理）。SyncReport{added, updated, skipped} 可观测。
"""

import re
from dataclasses import dataclass

from workbench.knowledge.vault import ALLOWED_FOLDERS, VaultStore
from workbench.knowledge.vector import VectorStore, content_hash

# create_note 的文件名约定 {date}-{title}.md：剥日期前缀还原展示标题
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


@dataclass
class SyncReport:
    added: int
    updated: int
    skipped: int


def _title_from_stem(stem: str) -> str:
    return _DATE_PREFIX.sub("", stem)


def sync_vault(vault: VaultStore, vector: VectorStore) -> SyncReport:
    """扫描 Vault 白名单目录做增量同步：hash 命中跳过 / 变更重算 / 新增入库。"""
    report = SyncReport(added=0, updated=0, skipped=0)
    for folder in sorted(ALLOWED_FOLDERS):
        for path in vault.list_notes(folder):
            content = path.read_text(encoding="utf-8")
            doc_id = f"note-{path.stem}"
            existing = vector.get_hash(doc_id)
            if existing == content_hash(content):
                report.skipped += 1
                continue
            vector.add(doc_id, _title_from_stem(path.stem), content, path=str(path))
            if existing is None:
                report.added += 1
            else:
                report.updated += 1
    return report
