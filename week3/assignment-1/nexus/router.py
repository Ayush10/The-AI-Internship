"""API routes for the Nexus web UI."""

import json
import asyncio
import io
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/nexus", tags=["Nexus Multi-Agent"])

# In-memory cache for autoplay results
_autoplay_results: dict = {}

# ── Models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(description="User message to send to the agent system")
    session_id: str | None = Field(default=None, description="Existing session ID")

class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent: str
    tool_calls: list

# ── Helpers ─────────────────────────────────────────────────────────

def _sse(data: dict, event: str = "message") -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

# ── Endpoints ───────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint (fallback)."""
    from agent_runner import create_session, run_query

    session_id = request.session_id or await create_session()
    final_text = ""
    final_agent = "nexus_support_router"
    all_tool_calls = []

    async for event in run_query(session_id, request.message):
        if event["type"] == "final":
            final_text = event["content"]
            final_agent = event.get("agent", final_agent)
            all_tool_calls = event.get("tool_calls", [])
        elif event["type"] == "text" and not final_text:
            final_text = event.get("content", "")
            final_agent = event.get("agent", final_agent)

    return ChatResponse(
        response=final_text or "I wasn't able to generate a response. Please try again.",
        session_id=session_id,
        agent=final_agent,
        tool_calls=all_tool_calls,
    )


@router.get("/chat/stream")
async def chat_stream(message: str, session_id: str | None = None):
    """SSE endpoint for real-time agent activity streaming."""
    from agent_runner import create_session, run_query

    async def event_generator():
        sid = session_id or await create_session()
        yield _sse({"type": "session", "session_id": sid})

        try:
            async for event in run_query(sid, message):
                yield _sse(event)
        except Exception as e:
            yield _sse({"type": "error", "content": str(e)})

        yield _sse({"type": "done"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/autoplay")
async def autoplay(theme: str = Query(default="dark")):
    """Run all 3 test scenarios sequentially via SSE."""
    from agent_runner import create_session, run_query

    scenarios = [
        {
            "id": "billing",
            "name": "Billing Inquiry (MCP)",
            "message": "Hi, I was charged twice for my last order. My email is customer3@example.com. Can you check my recent orders and tell me what happened?",
            "expected_agent": "billing_agent",
        },
        {
            "id": "returns",
            "name": "Return Request (A2A)",
            "message": "I want to return order 3 because it arrived with a scratched case. Am I eligible and can you start the return?",
            "expected_agent": "returns_agent",
        },
        {
            "id": "escalation",
            "name": "Escalation (Angry Customer)",
            "message": "This is unacceptable. I've been waiting THREE WEEKS for my refund on the AI Training Credits and nobody is helping me. I want a manager NOW. If this is not fixed today I will file a chargeback and cancel my enterprise account.",
            "expected_agent": "escalation_agent",
        },
    ]

    async def event_generator():
        results = []
        total = len(scenarios)

        yield _sse({"type": "autoplay_start", "total_scenarios": total})

        for i, scenario in enumerate(scenarios):
            yield _sse({
                "type": "scenario_start",
                "index": i,
                "id": scenario["id"],
                "name": scenario["name"],
                "message": scenario["message"],
            })

            autoplay_user = f"autoplay_{scenario['id']}"
            sid = await create_session(user_id=autoplay_user)
            scenario_result = {
                "id": scenario["id"],
                "name": scenario["name"],
                "message": scenario["message"],
                "expected_agent": scenario["expected_agent"],
                "actual_agent": None,
                "response": "",
                "tool_calls": [],
                "events": [],
            }

            try:
                async for event in run_query(sid, scenario["message"], user_id=autoplay_user):
                    scenario_result["events"].append(event)
                    yield _sse({"type": "scenario_event", "index": i, "event_type": event["type"], **event})

                    if event["type"] == "routing":
                        scenario_result["actual_agent"] = event["agent"]
                    elif event["type"] == "tool_call":
                        scenario_result["tool_calls"].append(event)
                    elif event["type"] == "final":
                        scenario_result["response"] = event["content"]
                        scenario_result["actual_agent"] = scenario_result["actual_agent"] or event.get("agent")
                        scenario_result["tool_calls"] = event.get("tool_calls", scenario_result["tool_calls"])
            except Exception as e:
                scenario_result["response"] = f"Error: {e}"
                yield _sse({"type": "scenario_error", "index": i, "error": str(e)})

            # Check routing accuracy
            routing_correct = (
                scenario_result["actual_agent"] == scenario["expected_agent"]
                if scenario_result["actual_agent"]
                else False
            )
            scenario_result["routing_correct"] = routing_correct

            results.append(scenario_result)
            yield _sse({
                "type": "scenario_complete",
                "index": i,
                "routing_correct": routing_correct,
                "actual_agent": scenario_result["actual_agent"],
                "expected_agent": scenario["expected_agent"],
                "tool_call_count": len(scenario_result["tool_calls"]),
                "tool_names": [tc.get("tool", "") for tc in scenario_result["tool_calls"]],
                "message": scenario["message"],
                "response": (scenario_result["response"] or "")[:600],
            })

        # Cache results
        _autoplay_results["scenarios"] = results
        _autoplay_results["timestamp"] = datetime.now(timezone.utc).isoformat()
        _autoplay_results["routing_accuracy"] = sum(
            1 for r in results if r.get("routing_correct")
        ) / len(results)

        yield _sse({
            "type": "autoplay_complete",
            "routing_accuracy": _autoplay_results["routing_accuracy"],
            "total_tool_calls": sum(len(r["tool_calls"]) for r in results),
        })
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/results")
async def get_results():
    """Return cached autoplay results."""
    if not _autoplay_results:
        return {"status": "no_results", "message": "Run autoplay first to generate results."}
    return _autoplay_results


@router.get("/architecture")
def get_architecture():
    """Return Mermaid diagram source for the agent topology."""
    return {
        "mermaid": """graph TD
    User([Customer]) --> Router[Root Router Agent]
    Router -->|delegates| Billing[Billing Agent]
    Router -->|delegates| Returns[Returns Agent]
    Router -->|delegates| Escalation[Escalation Agent]
    Billing -->|MCP read-only| DB[(Supabase DB)]
    Escalation -->|MCP read-write| DB
    Returns -->|A2A Protocol| A2A[Returns A2A Service :8001]
    A2A --> T1[check_return_eligibility]
    A2A --> T2[initiate_return]
    T1 -->|REST API| DB
    T2 -->|REST API| DB

    classDef router fill:#059669,stroke:#047857,color:#fff
    classDef mcp fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef a2a fill:#7c3aed,stroke:#6d28d9,color:#fff
    classDef db fill:#d97706,stroke:#b45309,color:#fff
    classDef tool fill:#64748b,stroke:#475569,color:#fff
    classDef user fill:#0f172a,stroke:#1e293b,color:#fff

    class Router router
    class Billing,Escalation mcp
    class Returns,A2A a2a
    class DB db
    class T1,T2 tool
    class User user""",
    }


@router.get("/download/zip")
def download_zip():
    """Download all results as ZIP."""
    if not _autoplay_results:
        return Response(content="No results yet. Run autoplay first.", status_code=404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Results JSON
        zf.writestr(
            "nexus_results/results.json",
            json.dumps(_autoplay_results, indent=2, default=str),
        )

        # Results markdown
        md = _generate_results_markdown()
        zf.writestr("nexus_results/results.md", md)

        # Architecture diagram
        arch = get_architecture()
        zf.writestr("nexus_results/architecture.mmd", arch["mermaid"])

    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=nexus_results.zip"},
    )


def _generate_results_markdown() -> str:
    """Generate a markdown summary of autoplay results."""
    results = _autoplay_results
    if not results:
        return "# No Results\nRun autoplay first."

    lines = [
        "# Nexus Multi-Agent Support — Autoplay Results",
        f"\n**Generated:** {results.get('timestamp', 'N/A')}",
        f"**Routing Accuracy:** {results.get('routing_accuracy', 0):.0%}",
        "",
        "## Scenario Results",
        "",
    ]

    for s in results.get("scenarios", []):
        status = "PASS" if s.get("routing_correct") else "FAIL"
        lines.extend([
            f"### {s['name']} [{status}]",
            f"**Input:** {s['message']}",
            f"**Expected Agent:** {s['expected_agent']}",
            f"**Actual Agent:** {s.get('actual_agent', 'unknown')}",
            f"**Tool Calls:** {len(s.get('tool_calls', []))}",
            "",
            f"**Response:**",
            f"> {s.get('response', 'No response')[:500]}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)
