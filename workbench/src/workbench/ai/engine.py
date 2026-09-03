"""AI 引擎：分类打标、决策分析、笔记起草、闭环检查等能力。

LLM 是外部系统边界：结构化输出走 JSON，解析失败一律回退（不抛异常），
回退形态按"低置信/原文兜底"设计，由上游按契约消化。
"""

import json


class AIEngine:
    def __init__(self, llm):
        self.llm = llm

    def classify(self, text: str) -> str:
        system = (
            "你是分类助手。根据内容判断类型，只输出 '输入'、'决策'、'实践'、'复盘'、'创造' 之一。"
        )
        return self.llm.complete(system, text)

    def analyze_decision(self, text: str, history: list[dict] | None = None) -> dict:
        """决策层：结构化追问 + 多维分析 + 历史参照对照（M3-B1）。

        返回 question/dimensions/options/clarify/lean/history_view/confidence。
        history 来自 recall（R1 单向依赖）：只消费不检索。注入为结构化摘要
        （标题+200 字截断+score，非全文——与 judge_link 同款喂料边界：成本
        上界 + 近全卡误判）；反结果偏误（决策 5/6）：prompt 指令式区分
        "决策过程质量"与"结果好坏"，结果未知的参照不强行判断。
        """
        system = (
            "你是决策分析助手，服务于个人知识工作流的决策层。对用户输入做结构化分析与追问，"
            '只输出 JSON：{"question": "提炼的核心决策问题（一句话）", '
            '"dimensions": ["需权衡的关键维度，2-4 个"], '
            '"options": [{"name": "方案名", "pros": "优势", "cons": "代价或风险"}], '
            '"clarify": ["信息不足时待向用户追问的问题"], '
            '"lean": "基于已有信息的倾向与理由；信息不足则留空", '
            '"history_view": "历史参照对照：每条写当时怎么定、结果如何、为何成败，'
            "并对比当前与历史条件的差异；无历史参照或不相关则留空\", "
            '"confidence": 0.0}。'
            "confidence 反映信息充分度：缺少关键信息时给低于 0.6 的值，并在 clarify 里列出待澄清问题；"
            "信息足够时给 0.6-1.0 并给出 lean。"
            "对照历史参照时严格区分决策过程质量与结果好坏：结果好可能只是运气，"
            "结果差也可能决策逻辑正确，不得因结果好坏高估或否定当时的决策逻辑；"
            "结果未知的参照不要强行判断好坏。"
        )
        user = text
        if history:
            user = f"{text}\n\n历史参照（用户过去的相关决策，按相似度递减）：\n" + "\n".join(
                f"{i}. 标题：{h.get('title', '')}（相似度 {h.get('score', '')}）\n"
                f"   摘要：{str(h.get('content', ''))[:200]}"
                for i, h in enumerate(history, 1)
            )
        raw = self.llm.complete(system, user)
        defaults: dict = {
            "question": raw if raw else "",
            "dimensions": [],
            "options": [],
            "clarify": [],
            "lean": "",
            "history_view": "",
            "confidence": 0.0,
        }
        data = self._parse_json(raw)
        return defaults if data is None else {**defaults, **data}

    def draft_note(self, kind: str, text: str) -> dict:
        """实践层：把结论/待办起草为可落库笔记。返回 title/content。

        契约（闭环依赖）：决策备忘正文必含「关联问题」节；待办正文必含「下一步」与「次日跟进」。
        """
        system = (
            "你是行动转化助手，服务于个人知识工作流的实践层。把用户的结论或待办转化为可直接落库的笔记，"
            '只输出 JSON：{"title": "标题（20 字内）", "content": "markdown 正文"}。'
            "规则：kind=决策备忘 时，正文依次含「背景」「决定」「关联问题」三节，"
            "「关联问题」写该决策待验证的 1-3 个问题；"
            "kind=待办 时，正文含「下一步」与「次日跟进」两节，"
            "「次日跟进」写具体时间或触发条件。正文用中文，不编造用户没给的事实。"
        )
        raw = self.llm.complete(system, f"kind={kind}\n{text}")
        defaults = {"title": text[:20], "content": text}
        data = self._parse_json(raw)
        return defaults if data is None else {**defaults, **data}

    def check_closed_loop(self, decisions: list[str]) -> list[str]:
        """检查决策闭环率：返回缺少关联的决策问题清单。实际实现可调用 LLM 语义判断，此处按规则返回。"""
        problems = []
        for d in decisions:
            if "关联问题" not in d:
                problems.append(f"{d} 缺少关联问题")
        return problems

    def judge_link(self, title: str, content: str, candidate: dict) -> dict:
        """知识层：判断新卡与既有候选卡是否值得建立双链。返回 {link_to, confidence}。

        喂料边界（M2-A）：仅 标题+摘要（200 字截断）+score——长文不放大 token，
        且近全卡会误判同名词卡。安全默认（M2-B1）：非法 JSON / 非 dict /
        link_to 非 bool 一律不链——宁可不链，不可误链。
        """
        system = (
            "你是知识关联判断助手，服务于个人知识库的双链建设。判断新笔记与既有笔记是否值得"
            "建立双向链接（同一主题、直接因果、同一事项的后续）。"
            '只输出 JSON：{"link_to": true/false, "confidence": 0.0到1.0}。'
            "只有明确相关才给 true；不确定或仅字面相似给 false。"
        )
        cand = (
            f"标题：{candidate.get('title', '')}\n"
            f"摘要：{str(candidate.get('content', ''))[:200]}\n"
            f"相似度：{candidate.get('score', 0.0)}"
        )
        raw = self.llm.complete(
            system, f"新笔记标题：{title}\n新笔记摘要：\n{content[:200]}\n\n候选笔记：\n{cand}"
        )
        defaults: dict = {"link_to": False, "confidence": 0.0}
        data = self._parse_json(raw)
        if data is None:
            return defaults
        merged = {**defaults, **data}
        if not isinstance(merged["link_to"], bool):
            return {**merged, "link_to": False}
        return merged

    def _parse_json(self, raw: str) -> dict | None:
        """LLM 边界：非法 JSON / 非 dict 一律返回 None，由调用方按各自默认值兜底。"""
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None
