"""最小 eval runner + 坏例回流（M1-B4，评测水位=选项 1：繁重评测集/盲测留 M5+）。

Golden case = 确定性脚本（CaseEngine/CaseVector 不调真 LLM）+ 输入 + resume 序列
+ expect 断言（status / output 子集 / tools / events，均可选）。
run_case 每.case 独立 vault 跑真 Orchestrator；load_cases 扫目录（一 case 一文件）
——回流产物落 evals/golden/，test_eval.py 全量跑，golden case 即 CI 回归。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from workbench.ai.orchestrator import Orchestrator, TurnResult
from workbench.ai.skills.base import SkillContext
from workbench.ai.trace import Trace
from workbench.knowledge.vault import VaultStore

DEFAULT_RELATED = [{"id": "n1", "title": "相关经验", "score": 0.9}]
DEFAULT_ANALYSIS = {
    "question": "",
    "dimensions": [],
    "options": [],
    "clarify": [],
    "lean": "",
    "confidence": 0.85,
}
DEFAULT_DRAFT = {"title": "草稿", "content": "草稿内容"}


class CaseEngine:
    """按 golden case 脚本回放的确定性引擎（eval 不调真 LLM）。"""

    def __init__(self, script: dict):
        self.script = script

    def classify(self, text: str) -> str:
        return str(self.script.get("label", "决策"))

    def analyze_decision(self, text: str) -> dict:
        return dict(self.script.get("analysis") or DEFAULT_ANALYSIS)

    def draft_note(self, kind: str, text: str) -> dict:
        return dict(self.script.get("draft") or DEFAULT_DRAFT)

    def check_closed_loop(self, decisions: list[str]) -> list[str]:
        return list(self.script.get("review_missing", []))

    def judge_link(self, title: str, content: str, candidate: dict) -> dict:
        judges = self.script.get("judges") or {}
        verdict = judges.get(candidate.get("title", ""))
        if verdict:
            return dict(verdict)
        return {"link_to": False, "confidence": 0.0}  # 未脚本化的候选默认不链（安全默认）


class CaseVector:
    def __init__(self, script: dict):
        self.script = script

    def search(self, query: str, top_k: int) -> list[dict]:
        related = self.script.get("related") or DEFAULT_RELATED
        return [dict(r) for r in related[:top_k]]

    def add(self, doc_id: str, title: str, content: str, path: str = "") -> None:
        return None  # 协议一致性：eval 重放只检索不落索引


@dataclass
class GoldenCase:
    id: str
    name: str
    input: str
    script: dict = field(default_factory=dict)
    resumes: list[dict] = field(default_factory=list)
    expect: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "input": self.input,
            "script": self.script,
            "resumes": self.resumes,
            "expect": self.expect,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=1)

    @classmethod
    def from_dict(cls, d: dict) -> "GoldenCase":
        return cls(
            id=str(d["id"]),
            name=str(d.get("name", d["id"])),
            input=str(d.get("input", "")),
            script=dict(d.get("script", {})),
            resumes=[dict(r) for r in d.get("resumes", [])],
            expect=dict(d.get("expect", {})),
        )


@dataclass
class CaseResult:
    id: str
    name: str
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    total: int
    passed: int
    failed: int
    results: list[CaseResult]

    def summary(self) -> str:
        lines = [f"eval: {self.passed}/{self.total} 通过"]
        for r in self.results:
            for f in r.failures:
                lines.append(f"  FAIL {r.id}: {f}")
        return "\n".join(lines)


def _check_expect(expect: dict, result: TurnResult, orch: Orchestrator) -> list[str]:
    failures: list[str] = []
    if "status" in expect and result.status != expect["status"]:
        failures.append(f"status: expect {expect['status']!r}, got {result.status!r}")
    for k, v in expect.get("output", {}).items():
        got = result.output.get(k)
        if got != v:
            failures.append(f"output.{k}: expect {v!r}, got {got!r}")
    if "tools" in expect:
        tools = [e.tool for e in orch.events if e.event == "step"]
        if tools != expect["tools"]:
            failures.append(f"tools: expect {expect['tools']}, got {tools}")
    if "events" in expect:
        names = [e.event for e in orch.events]
        if names != expect["events"]:
            failures.append(f"events: expect {expect['events']}, got {names}")
    return failures


def run_case(case: GoldenCase, workdir: str | Path) -> CaseResult:
    if "/" in case.id or "\\" in case.id or ".." in case.id:
        # case.id 拼进 vault 路径，外部 JSON 数据笔误即目录逃逸——入口即拒
        return CaseResult(case.id, case.name, False, [f"runtime: 非法 case id: {case.id!r}"])
    vault_dir = Path(workdir) / f"case-{case.id}" / "vault"
    ctx = SkillContext(
        CaseEngine(case.script), VaultStore(str(vault_dir)), CaseVector(case.script)
    )
    orch = Orchestrator(ctx)
    try:
        result = orch.run(case.input)
        for decision in case.resumes:
            result = orch.resume(decision)
    except Exception as e:  # eval 只报告不崩（如非法 resume 序列）
        return CaseResult(case.id, case.name, False, [f"runtime: {e}"])
    failures = _check_expect(case.expect, result, orch)
    return CaseResult(case.id, case.name, not failures, failures)


def run_cases(cases: list[GoldenCase], workdir: str | Path) -> EvalReport:
    results = [run_case(c, workdir) for c in cases]
    passed = sum(1 for r in results if r.passed)
    return EvalReport(len(results), passed, len(results) - passed, results)


def load_cases(path: str | Path) -> list[GoldenCase]:
    """目录（*.json 每文件一 case，按名排序）或单文件；不存在返回空。"""
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.json"))
    elif p.is_file():
        files = [p]
    else:
        return []
    return [GoldenCase.from_dict(json.loads(f.read_text(encoding="utf-8"))) for f in files]


def case_from_trace(
    trace: Trace, case_id: str, name: str = "", expect: dict | None = None
) -> GoldenCase:
    """坏例回流：从 trace 提取 input/script/resumes 生成 case。

    expect 缺省从当前结果起草（回归=固化当前行为）；坏例场景人工校对为正确行为后
    落盘 evals/golden/。script 从各 step 结果提取（decision 去 needs_judgement——
    重放时由 Skill 按 confidence 重新推导；recall 结果进 related 供 CaseVector 复现；
    link 的 judged 明细进 judges 供 CaseEngine 精确复现 LLM 档裁决）。
    """
    script: dict = {}
    resumes: list[dict] = []
    for e in trace.events:
        if e.get("event") == "step":
            tool = e.get("tool", "")
            result = e.get("result", {})
            if tool == "classify":
                script["label"] = result.get("label", "")
            elif tool == "decision":
                script["analysis"] = {k: v for k, v in result.items() if k != "needs_judgement"}
            elif tool == "action" and result.get("status") == "needs_confirmation":
                script["draft"] = {"title": result.get("title", ""), "content": result.get("content", "")}
            elif tool == "review":
                script["review_missing"] = list(result.get("missing", []))
            elif tool == "link":
                judged = list(result.get("judged", []))
                if judged:
                    script["judges"] = {
                        str(j.get("title", "")): {
                            "link_to": bool(j.get("link_to", False)),
                            "confidence": j.get("confidence", 0.0),
                        }
                        for j in judged
                    }
            elif tool == "recall":
                script["related"] = [dict(r) for r in result.get("results", [])]
        elif e.get("event") == "resume" and e.get("human_decision"):
            resumes.append(dict(e["human_decision"]))
    return GoldenCase(
        id=case_id,
        name=name or case_id,
        input=str(trace.meta.get("input", "")),
        script=script,
        resumes=resumes,
        expect=expect if expect is not None else _default_expect(trace),
    )


def _default_expect(trace: Trace) -> dict:
    last = trace.events[-1] if trace.events else {}
    status = str(trace.meta.get("status", ""))
    if last.get("event") == "finish":
        # path 是运行期落盘路径（tmp 各异），不入 expect
        output = {k: v for k, v in dict(last.get("result", {})).items() if k != "path"}
        return {"status": status, "output": output}
    if last.get("event") == "error":
        return {"status": status, "output": {"error": last.get("reason", "")}}
    return {"status": status}
