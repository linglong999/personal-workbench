"""Obsidian Vault 文件读写。"""
from pathlib import Path

# 允许写入的知识库目录
ALLOWED_FOLDERS = {"问题整理", "知识卡片", "决策备忘", "行动记录", "复盘沉淀", "愿景与原则"}


class VaultStore:
    def __init__(self, vault_path: str):
        self.root = Path(vault_path)

    def create_note(self, folder: str, title: str, content: str) -> Path:
        if folder not in ALLOWED_FOLDERS:
            raise ValueError(f"未知目录: {folder}")
        folder_path = self.root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        from datetime import date
        safe = title.replace("/", "-")
        path = folder_path / f"{date.today().isoformat()}-{safe}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def list_notes(self, folder: str) -> list[Path]:
        folder_path = self.root / folder
        if not folder_path.exists():
            return []
        return sorted(folder_path.glob("*.md"))

    def read_all_notes(self, folder: str) -> list[str]:
        """读取目录下所有笔记的文本内容，供 Agent 扫描。"""
        return [p.read_text(encoding="utf-8") for p in self.list_notes(folder)]