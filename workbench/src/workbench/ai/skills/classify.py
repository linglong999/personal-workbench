"""classify Skill：输入分类打标（迁自 ClassifierAgent，M1-B1）。"""

from workbench.ai.skills.base import SkillContext, SkillResult


class ClassifySkill:
    name = "classify"
    description = "输入分类打标：判断内容属于 输入/决策/实践/复盘/创造 哪一类。"
    requires_confirmation = False

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        label = ctx.engine.classify(args["text"])
        return SkillResult(output={"label": label})
