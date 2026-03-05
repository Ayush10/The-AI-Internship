"""Nexus Support Root Agent — routes to billing, returns, and escalation specialists."""

import os
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from .prompts import ROOT_INSTRUCTION, BILLING_INSTRUCTION, ESCALATION_INSTRUCTION
from .tools_supabase import get_supabase_toolset

MODEL = "gemini-2.5-flash"

# Supabase MCP connections
supabase_readonly = get_supabase_toolset(read_only=True)
supabase_readwrite = get_supabase_toolset(read_only=False)

# Sub-agent 1: Billing (read-only MCP — stretch goal: tool filtering)
billing_agent = Agent(
    model=MODEL,
    name="billing_agent",
    description=(
        "Handles billing inquiries including charges, invoices, payment history, "
        "order lookups, duplicate charge detection, and refund investigations. "
        "Has read-only access to the customer and orders database."
    ),
    instruction=BILLING_INSTRUCTION,
    tools=[supabase_readonly],
)

# Sub-agent 2: Escalation (read-write MCP — creates/updates tickets)
escalation_agent = Agent(
    model=MODEL,
    name="escalation_agent",
    description=(
        "Handles angry, frustrated, or high-stakes customer situations. "
        "Creates escalated support tickets with urgent priority. "
        "Use when the customer demands a manager, threatens chargebacks, "
        "or uses aggressive language."
    ),
    instruction=ESCALATION_INSTRUCTION,
    tools=[supabase_readwrite],
)

# Sub-agent 3: Returns (remote A2A service)
RETURNS_A2A_URL = os.environ.get("RETURNS_A2A_URL", "http://localhost:8001")
returns_agent_remote = RemoteA2aAgent(
    name="returns_agent",
    description=(
        "Handles product return requests. Can check if an order is eligible "
        "for return and initiate the return process with an RMA number. "
        "Use when the customer wants to return, exchange, or send back a product."
    ),
    agent_card=f"{RETURNS_A2A_URL}/.well-known/agent-card.json",
)

# Root router agent
root_agent = Agent(
    model=MODEL,
    name="nexus_support_router",
    description="Nexus Customer Support Router — analyzes customer intent and delegates to the appropriate specialist.",
    instruction=ROOT_INSTRUCTION,
    sub_agents=[billing_agent, escalation_agent, returns_agent_remote],
)
