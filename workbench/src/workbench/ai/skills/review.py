"""review Skill：复盘扫描（迁自 ReviewerAgent，M1-B1）。"""

from workbench.ai.skills.base import SkillContext, SkillResult


class ReviewSkill:
    name = "review"
    description = "复盘扫描：检查决策备忘闭环，找出缺关联问题的决策。"
    requires_confirmation = False

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        notes = ctx.vault.read_all_notes(args.get("folder", "决策备忘"))
        missing = ctx.engine.check_closed_loop(notes)
        return SkillResult(output={"missing": missing})
