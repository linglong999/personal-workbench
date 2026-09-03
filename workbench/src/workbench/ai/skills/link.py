"""link Skill：知识层——写卡自动双链的三档分流决策（M2-B1 新写，第 6 个 Skill）。

主管在 action 草稿后召回候选（recall top_k=20）并把候选经 args 传入；分流语义：
  score >= 0.85  auto：直接链，零 LLM；
  0.75 ~ 0.85    LLM 档：engine.judge_link 边缘判断，非法/残缺裁决一律不链；
  score < 0.75   pending_review：不自动链，confirm 时透出给用户裁决。
去重（同标题留最高分）+ 排除草稿正文已有的人工 [[链]]（尊重显式边）。
judged 明细进 result：trace 可回放、坏例回流可精确复现（eval CaseEngine.judges）。
"""

import re

from workbench.ai.skills.base import SkillContext, SkillResult

AUTO_THRESHOLD = 0.85
LLM_THRESHOLD = 0.75

_WIKILINK = re.compile(r"\[\[(.+?)\]\]")


class LinkSkill:
    name = "link"
    description = "知识关联：判断新卡与既有卡是否建立双链（三档阈值分流，宁可不链不可误链）。"
    requires_confirmation = False

    def run(self, ctx: SkillContext, args: dict) -> SkillResult:
        title = str(args.get("title", ""))
        content = str(args.get("content", ""))
        manual = {m.strip() for m in _WIKILINK.findall(content)}
        best: dict[str, dict] = {}  # 同标题去重留最高分（候选顺序不作降序假设）
        for c in args.get("candidates") or []:
            t = str(c.get("title", "")).strip()
            if not t or t in manual:
                continue
            score = c.get("score")
            if not isinstance(score, (int, float)):
                score = 0.0  # 旧数据无 score：按最低档处理
            if t not in best or score > best[t]["score"]:
                best[t] = {**c, "score": float(score)}
        links: list[str] = []
        pending: list[dict] = []
        judged: list[dict] = []
        for c in best.values():
            if c["score"] >= AUTO_THRESHOLD:
                links.append(c["title"])
            elif c["score"] >= LLM_THRESHOLD:
                verdict = ctx.engine.judge_link(title, content, c)
                ok = verdict.get("link_to") is True  # 非 True（缺省/类型残缺）一律不链
                if ok:
                    links.append(c["title"])
                judged.append(
                    {
                        "title": c["title"],
                        "score": c["score"],
                        "link_to": ok,
                        "confidence": verdict.get("confidence", 0.0),
                    }
                )
            else:
                pending.append({"title": c["title"], "score": c["score"]})
        return SkillResult(output={"links": links, "pending_review": pending, "judged": judged})
