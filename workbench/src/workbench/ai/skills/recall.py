"""recall Skill：经验召回（迁自 CoachAgent，M1-B1）。"""

from workbench.ai.skills.base import SkillContext, SkillResult


class RecallSkill:
    name = "recall"
    description = "经验召回：按任务主题检索历史知识，把最相关经验递到面前。"
    requires_confirmation = False

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        results = ctx.vector.search(args["task"], args.get("top_k", 5))
        return SkillResult(output={"results": results})
