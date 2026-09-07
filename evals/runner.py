"""Run the golden question set against the agent and score the results.

Usage:
    uv run python evals/runner.py
    uv run python evals/runner.py --repeats 3
    uv run python evals/runner.py --only point_nvda_margin
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import yaml

from palimpsest.agent.graph import build_graph
from palimpsest.config import settings
from palimpsest.embedding import OllamaEmbedder

GOLDEN = Path(__file__).parent / "golden.yaml"
RESULTS = Path(__file__).parent / "results"


@dataclass
class Result:
    id: str
    shape: str
    run: int
    passed: bool
    failures: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    citation_problems: list[str] = field(default_factory=list)
    answer: str = ""
    latency_ms: int = 0


def _tools_called(messages: list[dict]) -> list[str]:
    names = []
    for m in messages:
        for call in m.get("tool_calls") or []:
            names.append(call["name"])
    return names


def score(case: dict, messages: list[dict], citation_problems: list[str]) -> Result:
    expect = case.get("expect", {})
    answer = messages[-1].get("content") or ""
    called = _tools_called(messages)
    failures = []

    for needle in expect.get("contains", []):
        if needle.lower() not in answer.lower():
            failures.append(f"missing {needle!r}")

    for needle in expect.get("absent", []):
        if needle.lower() in answer.lower():
            failures.append(f"present but should not be: {needle!r}")

    for tool in expect.get("tools", []):
        if tool not in called:
            failures.append(f"tool not called: {tool}")

    if expect.get("citations_valid") and citation_problems:
        failures.append(f"citation problems: {'; '.join(citation_problems)}")

    return Result(
        id=case["id"],
        shape=case.get("shape", ""),
        run=0,
        passed=not failures,
        failures=failures,
        tools_called=called,
        citation_problems=citation_problems,
        answer=answer,
    )


def run_case(graph, case: dict) -> Result:
    start = time.monotonic()
    state = graph.invoke(
        {
            "messages": [{"role": "user", "content": case["question"]}],
            "iterations": 0,
        }
    )
    result = score(case, state["messages"], state.get("citation_problems") or [])
    result.latency_ms = int((time.monotonic() - start) * 1000)
    return result


def report(results: list[Result]) -> None:
    total = len(results)
    passed = sum(r.passed for r in results)

    print()
    print(f"{'id':<32} {'shape':<18} {'run':>3}  result")
    print("-" * 72)
    for r in results:
        mark = "pass" if r.passed else "FAIL"
        print(f"{r.id:<32} {r.shape:<18} {r.run:>3}  {mark}")
        for f in r.failures:
            print(f"{'':<55}{f}")

    print("-" * 72)
    print(f"{passed}/{total} passed ({passed / total:.0%})")

    by_shape: dict[str, list[Result]] = {}
    for r in results:
        by_shape.setdefault(r.shape, []).append(r)
    print()
    for shape, rs in sorted(by_shape.items()):
        p = sum(x.passed for x in rs)
        print(f"  {shape:<18} {p}/{len(rs)}")

    with_citations = [r for r in results if not r.citation_problems]
    print()
    print(f"citation checks clean: {len(with_citations)}/{total}")
    print(f"median latency: {sorted(r.latency_ms for r in results)[total // 2]} ms")


def save(results: list[Result]) -> Path:
    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = RESULTS / f"{stamp}.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": r.id,
                    "shape": r.shape,
                    "run": r.run,
                    "passed": r.passed,
                    "failures": r.failures,
                    "tools_called": r.tools_called,
                    "citation_problems": r.citation_problems,
                    "latency_ms": r.latency_ms,
                    "answer": r.answer,
                }
                for r in results
            ],
            indent=2,
        )
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--only", help="run a single case by id")
    args = parser.parse_args()

    cases = yaml.safe_load(GOLDEN.read_text())
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
        if not cases:
            print(f"no case with id {args.only!r}")
            return 1

    embedder = OllamaEmbedder(settings.embedding_model)
    model = build_model()

    results: list[Result] = []
    with psycopg.connect(settings.db_url) as conn:
        graph = build_graph(conn, embedder, model)
        for run in range(args.repeats):
            for case in cases:
                print(f"  [{run + 1}/{args.repeats}] {case['id']} ...", flush=True)
                r = run_case(graph, case)
                r.run = run + 1
                results.append(r)

    report(results)
    path = save(results)
    print(f"\nsaved to {path}")

    return 0 if all(r.passed for r in results) else 1


def build_model():
    """Same construction the CLI uses."""
    from palimpsest.cli import _build_llm

    return _build_llm(
        settings.agent_provider,
        settings.agent_model,
        settings.anthropic_api_key,
    )


if __name__ == "__main__":
    sys.exit(main())
