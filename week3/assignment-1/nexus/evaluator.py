"""Custom evaluator for the web UI Results tab."""

import json
from pathlib import Path


EVAL_CASES = json.loads(
    (Path(__file__).parent / "eval" / "eval_cases.json").read_text()
)


async def run_evaluation() -> dict:
    """Run all eval cases and return structured results."""
    from agent_runner import create_session, run_query

    results = []

    for case in EVAL_CASES:
        sid = await create_session()
        actual_agent = None
        response_text = ""
        tool_names = []

        async for event in run_query(sid, case["message"]):
            if event["type"] == "routing":
                actual_agent = event["agent"]
            elif event["type"] == "tool_call":
                tool_names.append(event.get("tool", ""))
            elif event["type"] == "text":
                response_text = event.get("content", "")
            elif event["type"] == "final":
                response_text = event.get("content", response_text)
                actual_agent = actual_agent or event.get("agent")

        routing_correct = actual_agent == case["expected_agent"]
        tools_present = all(t in tool_names for t in case["expected_tools"])
        keywords_found = all(
            kw.lower() in response_text.lower()
            for kw in case["expected_keywords"]
        )

        results.append({
            "id": case["id"],
            "name": case["name"],
            "message": case["message"],
            "expected_agent": case["expected_agent"],
            "actual_agent": actual_agent,
            "routing_correct": routing_correct,
            "expected_tools": case["expected_tools"],
            "actual_tools": tool_names,
            "tools_present": tools_present,
            "keywords_found": keywords_found,
            "response_preview": response_text[:300],
            "passed": routing_correct and tools_present,
        })

    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "accuracy": passed / len(results) if results else 0,
        "results": results,
    }
