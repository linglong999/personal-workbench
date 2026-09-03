"""action Skill：实践层——把结论/待办转化为可执行项落库（M1-B2 新写）。

confirm 语义（B3 主管接线）：主管见 requires_confirmation=True 先发 confirm
interrupt 把预览递给人；用户确认后才带 confirmed=True 调 run。未确认时本 Skill
零副作用（幂等），预览已含起草内容供 interrupt 展示。
kind→folder 显式映射：待办落「行动记录」（Vault 白名单目录，六层框架的实践层）。
写入即索引（B5 契约）：确认写入后同步向量库——recall 才能召回 agent 写的卡，
与 create_note 端点的「写后立即可检索」契约一致（所有入口一致）。
"""

from workbench.ai.skills.base import SkillContext, SkillResult

KIND_FOLDERS = {"决策备忘": "决策备忘", "待办": "行动记录"}


class ActionSkill:
    name = "action"
    description = "行动转化：把结论或待办起草为决策备忘/待办写入 Vault（备忘含关联问题，待办含次日跟进）；写库前需确认。"
    requires_confirmation = True

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        kind = args.get("kind", "决策备忘")
        if kind not in KIND_FOLDERS:
            raise ValueError(f"unknown kind: {kind}")  # 不论是否确认，入口即拒绝
        draft = ctx.engine.draft_note(kind, args["text"])
        if not args.get("confirmed"):
            return SkillResult(
                output={"status": "needs_confirmation", "kind": kind, **draft}
            )
        path = ctx.vault.create_note(KIND_FOLDERS[kind], draft["title"], draft["content"])
        ctx.vector.add(f"note-{path.stem}", draft["title"], draft["content"], path=str(path))
        return SkillResult(
            output={"status": "written", "kind": kind, "path": str(path)}
        )
