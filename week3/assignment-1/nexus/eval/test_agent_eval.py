"""Pytest runner for ADK agent evaluation."""

import json
import asyncio
from pathlib import Path

import pytest

EVAL_CASES = json.loads(
    (Path(__file__).parent / "eval_cases.json").read_text()
)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def runner(event_loop):
    from agent_runner import create_session, run_query
    return create_session, run_query


@pytest.mark.parametrize(
    "case",
    EVAL_CASES,
    ids=[c["id"] for c in EVAL_CASES],
)
@pytest.mark.asyncio
async def test_agent_routing(case, runner):
    """Verify each scenario routes to the expected agent."""
    create_session, run_query = runner
    sid = await create_session()
    actual_agent = None
    tool_names = []

    async for event in run_query(sid, case["message"]):
        if event["type"] == "routing":
            actual_agent = event["agent"]
        elif event["type"] == "tool_call":
            tool_names.append(event.get("tool", ""))
        elif event["type"] == "final":
            actual_agent = actual_agent or event.get("agent")

    assert actual_agent == case["expected_agent"], (
        f"Expected {case['expected_agent']}, got {actual_agent}"
    )
