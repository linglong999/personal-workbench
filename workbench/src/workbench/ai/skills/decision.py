"""decision Skill：决策层——结构化追问 + 多维分析（M1-B2 新写）。

只做分析不写库；低置信输出 needs_judgement 拍板标记（B3 主管映射
disambiguate/judgement interrupt，clarify 非空走 disambiguate）。
"""

from workbench.ai.skills.base import SkillContext, SkillResult


class DecisionSkill:
    name = "decision"
    description = "决策分析：提炼核心问题、多维权衡、产出可选方案与倾向；信息不足低置信时标记需人拍板。"
    requires_confirmation = False

    CONFIDENCE_THRESHOLD = 0.6  # 低于此值 → needs_judgement（对齐 M1-C interrupt 映射）

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        analysis = ctx.engine.analyze_decision(args["text"])
        try:
            confidence = float(analysis.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0  # LLM 边界：非法置信度按最低处理
        analysis["confidence"] = confidence
        analysis["needs_judgement"] = confidence < self.CONFIDENCE_THRESHOLD
        return SkillResult(output=analysis, confidence=confidence)
