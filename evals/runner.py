"""Run the golden question set against the agent.

uv run python evals/runner.py
uv run python evals/runner.py --only compare_nvda_margin_dip
uv run python evals/runner.py --shape absence --repeats 3
"""

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg
import yaml

from palimpsest.agent.graph import build_graph
from palimpsest.config import EVAL_RESULTS, settings
from palimpsest.embedding import OllamaEmbedder

GOLDEN = Path(__file__).parent / "golden.yaml"


def calls(messages: list[dict]) -> list[dict]:
    return [c for m in messages for c in (m.get("tool_calls") or [])]


def score(case: dict, messages: list[dict], problems: list[str]) -> dict:
    expect = case.get("expect", {})
    answer = messages[-1].get("content") or ""
    names = [c["name"] for c in calls(messages)]
    fails = []

    if not answer.strip():
        fails.append("empty answer")
    fails += [
        f"missing {n!r}"
        for n in expect.get("contains", [])
        if n.lower() not in answer.lower()
    ]
    fails += [
        f"unwanted {n!r}"
        for n in expect.get("absent", [])
        if n.lower() in answer.lower()
    ]
    fails += [
        f"tool not called: {t}" for t in expect.get("tools", []) if t not in names
    ]
    if expect.get("citations_valid") and problems:
        fails.append("citations: " + "; ".join(problems))

    return {
        "id": case["id"],
        "shape": case.get("shape", ""),
        "passed": not fails,
        "failures": fails,
        "tool_calls": [
            f"{c['name']}({json.dumps(c['args'], default=str)})"
            for c in calls(messages)
        ],
        "citation_problems": problems,
        "answer": answer,
    }


def run_case(graph, case: dict) -> dict:
    start = time.monotonic()
    try:
        state = graph.invoke(
            {
                "messages": [{"role": "user", "content": case["question"]}],
                "iterations": 0,
            }
        )
        result = score(case, state["messages"], state.get("citation_problems") or [])
    except Exception as e:  # noqa: BLE001 - one bad case must not lose the run
        result = {
            "id": case["id"],
            "shape": case.get("shape", ""),
            "passed": False,
            "failures": [f"error: {type(e).__name__}: {e}"],
            "tool_calls": [],
            "citation_problems": [],
            "answer": "",
        }
    result["latency_ms"] = int((time.monotonic() - start) * 1000)
    return result


def report(results: list[dict]) -> None:
    total, passed = len(results), sum(r["passed"] for r in results)
    print()
    for r in results:
        print(f"{r['id']:<32} {r['shape']:<18} {'pass' if r['passed'] else 'FAIL'}")
        for f in r["failures"]:
            print(f"        {f}")
        if not r["passed"]:
            for c in r["tool_calls"]:
                print(f"        -> {c}")

    print("-" * 64)
    print(f"{passed}/{total} passed ({passed / total:.0%})")

    shapes: dict[str, list[dict]] = {}
    for r in results:
        shapes.setdefault(r["shape"], []).append(r)
    for shape, rs in sorted(shapes.items()):
        print(f"  {shape:<18} {sum(x['passed'] for x in rs)}/{len(rs)}")

    clean = sum(not r["citation_problems"] for r in results)
    med = sorted(r["latency_ms"] for r in results)[total // 2]
    print(f"\ncitations clean: {clean}/{total}   median latency: {med} ms")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--only")
    p.add_argument("--shape")
    args = p.parse_args()

    cases = yaml.safe_load(GOLDEN.read_text())
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
    if args.shape:
        cases = [c for c in cases if c.get("shape") == args.shape]
    if not cases:
        print("no matching cases")
        return 1

    from palimpsest.llm import build_llm

    model = build_llm(
        settings.agent_provider, settings.agent_model, settings.anthropic_api_key
    )

    results = []
    with psycopg.connect(settings.db_url) as conn:
        graph = build_graph(conn, OllamaEmbedder(settings.embedding_model), model)
        for run in range(args.repeats):
            for case in cases:
                print(f"  [{run + 1}/{args.repeats}] {case['id']} ...", flush=True)
                results.append(run_case(graph, case) | {"run": run + 1})

    report(results)

    EVAL_RESULTS.mkdir(exist_ok=True)
    path = EVAL_RESULTS / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(results, indent=2))
    print(f"saved to {path}")

    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
