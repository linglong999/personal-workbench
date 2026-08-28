"""Obsidian Vault 文件读写。"""
import re
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
        from datetime import date, datetime
        safe = title.replace("/", "-")
        path = folder_path / f"{date.today().isoformat()}-{safe}.md"
        if path.exists():
            # 同日同题不覆盖旧笔记（会丢内容），追加时分秒后缀
            path = folder_path / f"{date.today().isoformat()}-{safe}-{datetime.now().strftime('%H%M%S')}.md"
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

    @staticmethod
    def _frontmatter_tags(text: str) -> list[str]:
        """从 Obsidian frontmatter 抽 tags（兼容 `- tag` 块列表）。"""
        m = re.search(r"^---\n(.*?)\n---", text, re.S)
        if not m:
            return []
        idx = m.group(1).find("tags:")
        if idx < 0:
            return []
        lines = m.group(1)[idx:].splitlines()[1:]
        tags = []
        for ln in lines:
            s = ln.strip()
            if s.startswith("- "):
                tags.append(s[2:].strip())
            elif s.startswith("-"):
                tags.append(s[1:].strip())
            else:
                break  # 遇到下一个 frontmatter 键，停止
        return tags

    def list_tags(self, folder: str = "知识卡片") -> dict[str, list[dict]]:
        """聚合目录下所有卡片的 frontmatter tags → {tag: [{title, path}]}。"""
        grouped: dict[str, list[dict]] = {}
        for p in self.list_notes(folder):
            text = p.read_text(encoding="utf-8")
            for tag in self._frontmatter_tags(text):
                entries = grouped.setdefault(tag, [])
                if not any(e["title"] == p.stem for e in entries):
                    entries.append({"title": p.stem, "path": str(p)})
        return dict(sorted(grouped.items()))