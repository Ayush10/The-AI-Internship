# Week 3 — Nexus Multi-Agent Support: Results Documentation

> **Assignment:** Build a multi-agent customer support system using Google ADK with MCP (Model Context Protocol) for database access and A2A (Agent-to-Agent) protocol for inter-service communication.
>
> **Stack:** Google ADK, Gemini 2.5 Flash, Supabase (self-hosted), MCP, A2A Protocol
>
> **Date:** March 4, 2026

---

## Table of Contents

1. [What I Built](#what-i-built)
2. [How It Works — Multi-Agent Architecture](#how-it-works--multi-agent-architecture)
3. [Agent Routing Results](#agent-routing-results)
4. [Three Test Scenarios](#three-test-scenarios)
5. [MCP Integration (Billing + Escalation)](#mcp-integration-billing--escalation)
6. [A2A Integration (Returns)](#a2a-integration-returns)
7. [Autoplay Feature](#autoplay-feature)
8. [Tech Stack](#tech-stack)
9. [How to Reproduce](#how-to-reproduce)

---

## What I Built

A multi-agent customer support system where a root router agent delegates incoming customer queries to three specialist agents based on intent:

- **Billing Agent (MCP)** — Handles charges, invoices, order lookups. Queries a real Supabase PostgreSQL database via the PostgREST MCP server. Read-only access.
- **Returns Agent (A2A)** — Handles product returns and exchanges. Runs as a separate HTTP service on port 8001, consumed via Google ADK's A2A protocol. Has its own tools (`check_return_eligibility`, `initiate_return`) that query Supabase REST API directly.
- **Escalation Agent (MCP)** — Handles angry customers and high-stakes situations. Creates/updates support tickets in Supabase with escalated status and urgent priority. Read-write access.

The system includes:
- **Interactive Chat** — Real-time SSE streaming with live agent routing badges and tool call activity log
- **Interactive Architecture** — Clickable topology diagram with node inspector panel showing connections, protocols, and configuration
- **Results Dashboard** — Autoplay runs all 3 test scenarios, shows routing accuracy, tool call counts, and expandable scenario cards with full agent responses
- **Dark Mode** — Full theme support

---

## How It Works — Multi-Agent Architecture

```
Customer → Root Router Agent (Gemini 2.5 Flash)
              ├── Billing Agent ──[MCP stdio]──→ @supabase/mcp-server-postgrest ──→ Supabase DB
              ├── Returns Agent ──[A2A HTTP]──→ Returns A2A Service (:8001)
              │                                   ├── check_return_eligibility ──→ Supabase REST API
              │                                   └── initiate_return ──→ Supabase REST API
              └── Escalation Agent ──[MCP stdio]──→ @supabase/mcp-server-postgrest ──→ Supabase DB
```

### Protocol Breakdown

| Protocol | Used By | How It Works |
|----------|---------|-------------|
| **MCP (Model Context Protocol)** | Billing + Escalation agents | Spawns `@supabase/mcp-server-postgrest` via stdio. Agent sends PostgREST HTTP requests (GET/POST/PATCH) through the MCP server to query/mutate the Supabase database. |
| **A2A (Agent-to-Agent)** | Returns agent | The returns agent runs as a standalone ADK agent exposed via `to_a2a()` on port 8001. The root agent consumes it via `RemoteA2aAgent`, which fetches the agent card from `/.well-known/agent-card.json` and communicates over HTTP. |
| **Gemini 2.5 Flash** | All agents | Google's fast, capable model. Used for intent classification (routing), database query generation (billing/escalation), and natural language responses (all agents). |

### Database Schema

Three tables in Supabase PostgreSQL:

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `customers` | Customer accounts | id, name, email, phone, plan, lifetime_value |
| `orders` | Order history | id, customer_id, product, amount, status, order_date, delivery_date, return_eligible |
| `support_tickets` | Support ticket tracking | id, customer_id, subject, description, status, priority, assigned_to |

Seeded with 5 customers, 12 orders (including a deliberate duplicate charge), and 8 support tickets.

---

## Agent Routing Results

The autoplay feature tests all 3 scenarios and measures routing accuracy:

| Scenario | Expected Agent | Actual Agent | Routing | Tool Calls |
|----------|---------------|--------------|---------|-----------|
| Billing Inquiry | billing_agent | billing_agent | PASS | postgrestRequest (customer lookup + order history) |
| Return Request | returns_agent | returns_agent | PASS | check_return_eligibility, initiate_return |
| Escalation (Angry Customer) | escalation_agent | escalation_agent | PASS | postgrestRequest (customer lookup + ticket creation) |

**Routing Accuracy: 100% (3/3)**

The root agent correctly identifies intent from the customer message and delegates to the appropriate specialist every time.

---

## Three Test Scenarios

### Scenario 1: Billing Inquiry (MCP)

**Input:** "Hi, I was charged twice for my last order. My email is customer3@example.com. Can you check my recent orders and tell me what happened?"

**Expected behavior:** Route to billing_agent → query customer by email → fetch orders → identify duplicate charge → explain finding.

**What happens:**
1. Root agent identifies billing intent, delegates to `billing_agent`
2. Billing agent calls `postgrestRequest` with `GET /customers?email=eq.customer3@example.com`
3. Billing agent calls `postgrestRequest` with `GET /orders?customer_id=eq.3&order_by=order_date.desc`
4. Agent finds orders, identifies the duplicate charge, explains findings to the customer
5. Recommends next steps for the refund

### Scenario 2: Return Request (A2A)

**Input:** "I want to return order 3 because it arrived with a scratched case. Am I eligible and can you start the return?"

**Expected behavior:** Route to returns_agent → check eligibility via A2A → if eligible, initiate return → provide RMA number.

**What happens:**
1. Root agent identifies return intent, delegates to `returns_agent` (remote A2A)
2. Returns A2A service calls `check_return_eligibility(order_id="3")`
3. Tool queries Supabase REST API: `GET /rest/v1/orders?id=eq.3&select=*`
4. Checks: status is "delivered", delivery date is within 30 days, not already returned
5. If eligible, calls `initiate_return(order_id="3", reason="scratched case")`
6. PATCHes order status to "returned", generates RMA number
7. Returns RMA number and return instructions to the customer

### Scenario 3: Escalation (Angry Customer)

**Input:** "This is unacceptable. I've been waiting THREE WEEKS for my refund on the AI Training Credits and nobody is helping me. I want a manager NOW. If this is not fixed today I will file a chargeback and cancel my enterprise account."

**Expected behavior:** Route to escalation_agent → acknowledge frustration → look up customer → create escalated ticket → provide ticket reference.

**What happens:**
1. Root agent detects aggressive language and escalation keywords, delegates to `escalation_agent`
2. Escalation agent acknowledges the customer's frustration with empathetic language
3. Calls `postgrestRequest` to look up the customer and any existing tickets
4. Creates a new support ticket with `POST /support_tickets` with status="escalated" and priority="urgent"
5. Provides the ticket ID as a reference number
6. Explains next steps: senior support manager review within 2 hours

---

## MCP Integration (Billing + Escalation)

The MCP connection uses `@supabase/mcp-server-postgrest` (official Supabase package) via stdio:

```python
McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=[
            "-y", "@supabase/mcp-server-postgrest",
            "--apiUrl", f"{SUPABASE_URL}/rest/v1",
            "--apiKey", api_key,
            "--schema", "public",
        ],
    )
)
```

This exposes two tools to the agents:
- **`postgrestRequest`** — Execute HTTP requests (GET/POST/PATCH/DELETE) against the PostgREST API
- **`sqlToRest`** — Convert SQL queries to PostgREST method+path (useful for complex queries)

The billing agent uses read-only access (anon key), while the escalation agent uses read-write access (service role key) to create/update tickets.

---

## A2A Integration (Returns)

The returns agent runs as a standalone service:

```python
# apps/returns_a2a/agent.py
returns_agent = Agent(
    model="gemini-2.5-flash",
    name="returns_agent",
    tools=[check_return_eligibility, initiate_return],
)
a2a_app = to_a2a(returns_agent, port=8001)
```

The root agent consumes it via `RemoteA2aAgent`:

```python
RemoteA2aAgent(
    name="returns_agent",
    description="Handles product return requests...",
    agent_card=f"{RETURNS_A2A_URL}/.well-known/agent-card.json",
)
```

The A2A protocol handles serialization, tool delegation, and response routing automatically. The returns service has its own tools that query Supabase directly via `httpx` (not MCP), keeping the architecture modular.

---

## Autoplay Feature

The **Autoplay** button in the Results tab runs all 3 test scenarios sequentially via SSE streaming:

### How It Works

1. **Scenario Start** — Creates a fresh ADK session for each scenario
2. **Agent Activity** — Streams routing decisions, tool calls, and intermediate text in real-time
3. **Scenario Complete** — Reports routing accuracy, tool call count, and response summary
4. **Final Summary** — Shows overall routing accuracy and total tool calls

### Live Agent Trace

During autoplay, a live trace log shows every event as it happens:
- `[ROUTING]` — Which sub-agent was selected
- `[TOOL]` — MCP/A2A tool calls with tool names
- `[TEXT]` — Intermediate agent responses
- `[FINAL]` — Complete agent response

### Results Display

After autoplay completes, the Results tab shows:
- **Summary Stats** — Routing accuracy percentage, total tool calls, agents used
- **Scenario Cards** — Expandable cards for each scenario with:
  - User query
  - Routing comparison (expected vs actual)
  - Tool call badges
  - Full agent response (markdown rendered)
- **Download** — ZIP bundle with results JSON and markdown

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Agent Framework** | Google ADK | Native support for MCP, A2A, sub-agent routing, and Gemini models |
| **LLM** | Gemini 2.5 Flash | Fast, capable, good at intent classification and tool use |
| **Database** | Supabase (self-hosted) | PostgreSQL + PostgREST API, deployed via Coolify on VPS |
| **MCP Server** | @supabase/mcp-server-postgrest | Official PostgREST MCP server, no stored procedures needed |
| **A2A Protocol** | Google ADK to_a2a() | Standard agent-to-agent communication over HTTP |
| **Backend** | FastAPI | Async SSE streaming, automatic API docs |
| **Frontend** | Vanilla JS + Tailwind CSS | Zero build tools, CDN-loaded |
| **Process Manager** | Supervisord | Runs both the A2A service (port 8001) and main app (port 8003) |
| **Deployment** | Docker + Coolify | Auto-deploy on push to main |

---

## How to Reproduce

```bash
# 1. Clone the repository
git clone https://github.com/Ayush10/The-AI-Internship.git
cd "The-AI-Internship/week3/assignment-1/nexus"

# 2. Copy and fill in environment variables
cp .env.example .env
# Set: GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Ensure Node.js is available (for npx to run MCP server)
node --version  # v18+ required

# 5. Set up the database
# Run db/schema.sql and db/seed.sql in your Supabase instance

# 6. Start the Returns A2A service
uvicorn apps.returns_a2a.agent:a2a_app --host 0.0.0.0 --port 8001 &

# 7. Start the main application
uvicorn main:app --host 0.0.0.0 --port 8003

# 8. Open in browser
# http://localhost:8003

# 9. Click "Run All Scenarios" in the Results tab to test everything
```

For Docker deployment:
```bash
docker compose up --build week3-nexus
# Access at http://localhost:8003 or via the gateway at /week3/nexus/
```

---

## What I Would Improve

1. **Persistent sessions** — Currently uses `InMemorySessionService`. A Redis-backed session store would persist conversations across restarts.
2. **Streaming agent responses** — The chat currently waits for the full response. Token-by-token streaming would improve perceived latency.
3. **More specialist agents** — Add shipping tracking, product recommendations, or FAQ agents to demonstrate more complex routing.
4. **Evaluation automation** — The 6-case eval suite in `eval/` should run as part of CI/CD.
5. **Agent observability** — Add tracing (OpenTelemetry) to track token usage, latency per agent, and MCP/A2A call durations.
