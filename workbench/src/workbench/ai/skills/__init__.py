"""Skill 单元层（M1-C）：每个价值环节一个可单测、可替换的原子单元。

包结构：base（协议）→ classify/review/recall/decision/action（实现）→ registry（调度入口）。
依赖方向：Skill → engine/vector/vault，不依赖主管（ADR-0001 D1 单向依赖）。
"""
