# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

## [0.2.0] - 2026-09-02

### Added（M0-B0 · 工程规范）

- ruff（lint + format，line-length 100，E/F/I/W 规则）接入 `workbench/pyproject.toml`
- mypy 静态类型检查（explicit_package_bases + mypy_path=src，`mypy src` 可用）
- pytest-cov 覆盖率门禁（分阶段收紧：B0=50% → B1=70% → M0 收口=85%）
- GitHub Actions CI（backend：lint / type check / test+coverage；frontend job 待 B2 启用）
- ADR-0001：分层架构、JWT 方案 A、取消公网/Docker、SQLite 选型、分阶段质量门槛
- `docs/architecture/index.md` 架构总览

### Fixed（B0 顺带，ruff/mypy 基线清理）

- 全仓 ruff format 格式化（20 文件）+ 29 处 lint 自动修复
- `ai/llm.py`：`complete()` 返回值兜底 None（`str | None` → `str`）
- `knowledge/vector.py`：`vec` 类型标注、`search()` 对 Chroma 可选字段的安全取值、
  `_LocalEmbeddingFunction.__call__` 与三方基类返回类型冲突的显式 `type: ignore[override]`
