# Nexus — Implementation Documentation

## Overview

Nexus is a multi-agent customer support system built for Week 3 of the AI Engineering Bootcamp. It demonstrates three key concepts:

1. **Multi-agent orchestration** using Google ADK with a root router delegating to specialist sub-agents
2. **MCP (Model Context Protocol)** for database access — billing and escalation agents query Supabase via MCP
3. **A2A (Agent-to-Agent protocol)** for inter-service communication — the returns agent runs as a separate microservice

## Architecture Decisions

### Why Google ADK?
ADK provides first-class support for multi-agent systems with built-in routing, MCP toolsets, and A2A protocol support. The `Agent` class supports `sub_agents` for delegation, and `RemoteA2aAgent` enables communication with external A2A services.

### Why self-hosted Supabase?
Self-hosted on VPS via Coolify for reuse across future projects. Supabase provides PostgreSQL + REST API + auth out of the box. The community `selfhosted-supabase-mcp` server bridges ADK agents to the self-hosted instance.

### Why A2A for returns?
The returns service demonstrates A2A protocol — running as an independent microservice on port 8001, exposed via `to_a2a()`. The root agent communicates with it through `RemoteA2aAgent`, which fetches the agent card from `/.well-known/agent-card.json`.

### Why Supervisord?
The Docker container runs two processes (returns A2A on 8001, main app on 8003). Supervisord manages both, starting the A2A service first (priority 10) before the main app (priority 20).

## File Inventory

### Core Agent Files

| File | Description |
|------|------------|
| `apps/support_root/agent.py` | Root router + billing + escalation agents, RemoteA2aAgent for returns |
| `apps/support_root/prompts.py` | Agent instructions (ROOT, BILLING, ESCALATION) |
| `apps/support_root/tools_supabase.py` | McpToolset factory — supports HTTP and stdio transport |
| `apps/returns_a2a/agent.py` | Returns agent + `to_a2a()` A2A service |
| `apps/returns_a2a/tools.py` | `check_return_eligibility`, `initiate_return` — queries Supabase REST API |

### Web Application

| File | Description |
|------|------------|
| `main.py` | FastAPI entrypoint, BASE_PATH injection, static file serving |
| `router.py` | API routes: chat, stream, autoplay, results, architecture, download |
| `agent_runner.py` | Bridge between FastAPI and ADK Runner with event parsing |
| `config.py` | Environment variable loading |

### Frontend

| File | Description |
|------|------------|
| `static/index.html` | 3-tab UI: Chat, Architecture, Results |
| `static/app.js` | SSE consumer, chat UI, autoplay, mermaid init, theme toggle |
| `static/style.css` | Glass morphism, agent badges, chat bubbles, animations |
| `static/favicon.svg` | Emerald gradient hub icon |

### Database

| File | Description |
|------|------------|
| `db/schema.sql` | 3 tables: customers, orders, support_tickets |
| `db/seed.sql` | 5 customers, 12 orders, 8 tickets — demo-optimized |

### Evaluation

| File | Description |
|------|------------|
| `eval/eval_cases.json` | 6 golden test cases |
| `eval/test_agent_eval.py` | Pytest runner for routing accuracy |
| `evaluator.py` | Web UI evaluator for Results tab |

### Deployment

| File | Description |
|------|------------|
| `Dockerfile` | Python 3.12 + Node.js + supervisord |
| `supervisord.conf` | Manages returns A2A (8001) + main app (8003) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Database Schema

### customers
- `id` SERIAL PK, `name`, `email` (UNIQUE), `phone`, `plan` (basic/pro/enterprise), `created_at`, `lifetime_value`

### orders
- `id` SERIAL PK, `customer_id` FK, `product`, `amount`, `status` (pending/shipped/delivered/returned/refunded), `order_date`, `delivery_date`, `return_eligible`, `return_by_date`

### support_tickets
- `id` SERIAL PK, `customer_id` FK, `order_id` FK (nullable), `subject`, `description`, `status` (open/in_progress/escalated/resolved/closed), `priority` (low/normal/high/urgent), `assigned_to`, `created_at`, `updated_at`

## API Endpoints

| Method | Path | Description |
|--------|------|------------|
| GET | `/` | Serves web UI |
| GET | `/health` | Health check |
| POST | `/api/nexus/chat` | Non-streaming chat |
| GET | `/api/nexus/chat/stream` | SSE streaming chat |
| GET | `/api/nexus/autoplay` | Run 3 test scenarios via SSE |
| GET | `/api/nexus/results` | Cached autoplay results |
| GET | `/api/nexus/architecture` | Mermaid diagram source |
| GET | `/api/nexus/download/zip` | Download results as ZIP |

## SSE Event Types

| Event | Fields | Description |
|-------|--------|------------|
| `session` | `session_id` | New session created |
| `routing` | `agent` | Sub-agent activated |
| `tool_call` | `tool`, `args` | MCP/A2A tool invocation |
| `tool_result` | `tool`, `result` | Tool response |
| `text` | `content`, `agent` | Intermediate text |
| `final` | `content`, `agent`, `tool_calls` | Complete response |
| `error` | `content` | Error message |
| `done` | - | Stream complete |

## Setup Instructions

### Prerequisites
- Python 3.12+
- Self-hosted Supabase instance (with schema + seed data applied)
- Google API key for Gemini

### Local Development
1. Copy `.env.example` to `.env` and fill in values
2. Run schema.sql and seed.sql against Supabase
3. Start returns A2A: `uvicorn apps.returns_a2a.agent:a2a_app --port 8001`
4. Start main app: `uvicorn main:app --port 8003`

### Docker Deployment
- The Dockerfile uses supervisord to run both services
- nginx reverse proxy routes `/week3/nexus/` to port 8003
- SSE support configured with `proxy_buffering off` and 600s timeout
