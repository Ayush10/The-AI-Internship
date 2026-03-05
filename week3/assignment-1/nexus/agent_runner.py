"""Bridge between FastAPI web UI and ADK Runner for programmatic agent invocation."""

import json
import asyncio
from typing import AsyncGenerator

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

import config  # noqa: F401 — triggers env var loading

from apps.support_root.agent import root_agent

APP_NAME = "nexus"

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


async def create_session(user_id: str = "web_user") -> str:
    """Create a new chat session, return session_id."""
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )
    return session.id


async def run_query(session_id: str, message: str, user_id: str = "web_user") -> AsyncGenerator[dict, None]:
    """Run a user query through the agent system.

    Yields structured event dicts:
      - {type: "routing", agent: str}         — which sub-agent is active
      - {type: "tool_call", tool: str, args: dict} — MCP/A2A tool invocations
      - {type: "text", content: str, agent: str}   — intermediate text
      - {type: "final", content: str, agent: str, tool_calls: list}
    """
    tool_calls = []
    current_agent = "nexus_support_router"

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=message)],
        ),
    ):
        # Track which agent is active
        author = getattr(event, "author", None) or ""
        if author and author != current_agent:
            current_agent = author
            yield {"type": "routing", "agent": current_agent}

        # Extract tool calls
        if hasattr(event, "actions") and event.actions:
            actions = event.actions
            if hasattr(actions, "tool_calls"):
                for tc in actions.tool_calls:
                    tool_name = getattr(tc, "name", str(tc))
                    tool_args = getattr(tc, "args", {})
                    call_info = {"tool": tool_name, "args": _safe_serialize(tool_args)}
                    tool_calls.append(call_info)
                    yield {"type": "tool_call", **call_info, "agent": current_agent}

        # Extract function call parts from content
        if hasattr(event, "content") and event.content:
            content = event.content
            if hasattr(content, "parts"):
                for part in content.parts:
                    # Function call
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        call_info = {
                            "tool": getattr(fc, "name", "unknown"),
                            "args": _safe_serialize(getattr(fc, "args", {})),
                        }
                        tool_calls.append(call_info)
                        yield {"type": "tool_call", **call_info, "agent": current_agent}

                    # Function response
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        yield {
                            "type": "tool_result",
                            "tool": getattr(fr, "name", "unknown"),
                            "result": _safe_serialize(getattr(fr, "response", {})),
                            "agent": current_agent,
                        }

                    # Text content
                    if hasattr(part, "text") and part.text:
                        yield {"type": "text", "content": part.text, "agent": current_agent}

        # Check if this is the final event
        if hasattr(event, "is_final_response") and event.is_final_response():
            text_parts = []
            if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)

            if text_parts:
                yield {
                    "type": "final",
                    "content": "\n".join(text_parts),
                    "agent": current_agent,
                    "tool_calls": tool_calls,
                }


def _safe_serialize(obj) -> dict | str:
    """Safely serialize an object to JSON-compatible format."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return str(obj)
