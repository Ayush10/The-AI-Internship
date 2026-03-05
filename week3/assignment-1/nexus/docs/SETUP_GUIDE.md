# Nexus — Step-by-Step Setup Guide

This document provides exact, copy-paste-ready instructions to get Nexus running. It is written for a Claude Code session on the VPS or local machine.

---

## Prerequisites

- VPS at `72.62.82.57` (SSH user: `ayush`)
- Coolify running on the VPS (manages Docker deployments)
- Google API key for Gemini (`GOOGLE_API_KEY`)
- Node.js 18+ (for the MCP server npx command)
- Python 3.12+

---

## Phase 1: Deploy Supabase on VPS via Coolify

### 1.1 — Open Coolify Dashboard

Go to the Coolify dashboard on the VPS. This is typically at `https://coolify.ayushojha.com` or whatever domain Coolify is configured on.

### 1.2 — Create a New Supabase Service

1. In Coolify, click **"+ New"** → **"Service"**
2. Search for **"Supabase"** in the one-click templates
3. Select the Supabase template
4. Choose a project/environment for it (e.g., "shared-services" or "infrastructure")
5. Click **Deploy**

Coolify will spin up all Supabase components:
- PostgreSQL database
- PostgREST (REST API)
- GoTrue (Auth)
- Kong (API Gateway)
- Studio (Dashboard UI)
- Realtime
- Storage

### 1.3 — Configure Domain (Optional but Recommended)

In the Coolify service settings:
- Set the Studio domain to something like `supabase.ayushojha.com`
- Or note the auto-assigned port/URL that Coolify provides
- Ensure HTTPS is enabled via Coolify's built-in Let's Encrypt

### 1.4 — Collect Credentials

After deployment, find these values from the Coolify Supabase service environment variables or the Studio dashboard:

| Variable | Where to Find | Example |
|----------|--------------|---------|
| `SUPABASE_URL` | Kong/API gateway URL | `https://supabase.ayushojha.com` or `http://72.62.82.57:<port>` |
| `SUPABASE_ANON_KEY` | Service env vars → `ANON_KEY` | `eyJhbGci...` (JWT) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service env vars → `SERVICE_ROLE_KEY` | `eyJhbGci...` (JWT) |
| `SUPABASE_DB_URL` | PostgreSQL connection string | `postgresql://postgres:<password>@<host>:5432/postgres` |

**Important:** The `SUPABASE_URL` must be the Kong API gateway URL, NOT the Studio URL. The REST API is at `{SUPABASE_URL}/rest/v1/`.

### 1.5 — Verify Supabase is Running

```bash
# Test the REST API (should return empty array or auth error)
curl -s -H "apikey: <ANON_KEY>" \
     -H "Authorization: Bearer <ANON_KEY>" \
     "<SUPABASE_URL>/rest/v1/" | head -c 200

# Test Studio (should return HTML)
curl -s "<SUPABASE_URL>" | head -c 100
```

---

## Phase 2: Create Database Tables and Seed Data

### 2.1 — Open Supabase SQL Editor

Open the Supabase Studio dashboard and go to **SQL Editor**.

### 2.2 — Run Schema SQL

Copy the entire contents of `db/schema.sql` and execute it in the SQL editor:

```sql
-- File: db/schema.sql
-- Creates 3 tables: customers, orders, support_tickets
-- Plus 4 indexes

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    plan TEXT NOT NULL DEFAULT 'basic' CHECK (plan IN ('basic', 'pro', 'enterprise')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    lifetime_value NUMERIC(10,2) DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product TEXT NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'shipped', 'delivered', 'returned', 'refunded')),
    order_date TIMESTAMPTZ DEFAULT NOW(),
    delivery_date TIMESTAMPTZ,
    return_eligible BOOLEAN DEFAULT TRUE,
    return_by_date TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_id INTEGER REFERENCES orders(id),
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'escalated', 'resolved', 'closed')),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    assigned_to TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON support_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
```

### 2.3 — Run Seed SQL

Copy the entire contents of `db/seed.sql` and execute it. This inserts:
- 5 customers (IDs 1-5)
- 12 orders (IDs 1-12)
- 8 support tickets (IDs 1-8)

Key test data points:
- **Sarah (customer 3, email: customer3@example.com)**: Has orders 4 and 5 — both are "Premium Keyboard - MX Keys" at $129.99, placed 2 minutes apart on Jan 20. This is the **duplicate charge scenario** for billing tests.
- **Bob (customer 2)**: Order 3 is "Wireless Noise-Canceling Headphones" delivered Feb 14, 2026 — **within 30-day return window**. This is the return test scenario.
- **Emily (customer 5)**: Has ticket 4 — an angry escalation about a 3-week-old refund. Order 10 is already refunded. This is the **escalation test scenario**.

### 2.4 — Verify Data

Run these queries in the SQL editor to confirm:

```sql
SELECT count(*) FROM customers;    -- Should be 5
SELECT count(*) FROM orders;       -- Should be 12
SELECT count(*) FROM support_tickets;  -- Should be 8

-- Verify duplicate charge scenario
SELECT id, product, amount, order_date FROM orders WHERE customer_id = 3 ORDER BY order_date;
-- Should show orders 4 and 5 both "Premium Keyboard - MX Keys" at 129.99

-- Verify return-eligible order
SELECT id, product, status, delivery_date, return_eligible FROM orders WHERE id = 3;
-- Should show delivered, return_eligible = true

-- Verify REST API works
-- (Do this via curl from terminal, not SQL editor)
```

### 2.5 — Verify REST API Access

```bash
# List all customers via REST API
curl -s \
  -H "apikey: <ANON_KEY>" \
  -H "Authorization: Bearer <ANON_KEY>" \
  "<SUPABASE_URL>/rest/v1/customers?select=id,name,email" | python3 -m json.tool

# Should return all 5 customers

# Verify order lookup (used by returns A2A tools)
curl -s \
  -H "apikey: <ANON_KEY>" \
  -H "Authorization: Bearer <ANON_KEY>" \
  "<SUPABASE_URL>/rest/v1/orders?id=eq.3&select=*" | python3 -m json.tool

# Should return Bob's headphones order
```

### 2.6 — Configure Row Level Security (RLS)

By default, Supabase enables RLS on new tables, which blocks all access. Either:

**Option A: Disable RLS (simplest for demo)**
```sql
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE orders DISABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets DISABLE ROW LEVEL SECURITY;
```

**Option B: Add permissive policies**
```sql
-- Allow anon key to read all tables
CREATE POLICY "allow_anon_read_customers" ON customers FOR SELECT USING (true);
CREATE POLICY "allow_anon_read_orders" ON orders FOR SELECT USING (true);
CREATE POLICY "allow_anon_read_tickets" ON support_tickets FOR SELECT USING (true);

-- Allow service key to write (for escalation agent)
CREATE POLICY "allow_service_write_tickets" ON support_tickets FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_service_write_orders" ON orders FOR UPDATE USING (true) WITH CHECK (true);
```

---

## Phase 3: Configure Environment Variables

### 3.1 — Create .env File

In the repo root (`The-AI-Internship/`), add these to the `.env` file:

```bash
# Google AI (Gemini for ADK agents)
GOOGLE_API_KEY=<your-gemini-api-key>
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Supabase (from Phase 1.4)
SUPABASE_URL=<kong-api-gateway-url>
SUPABASE_ANON_KEY=<anon-key-jwt>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key-jwt>

# MCP — leave empty to use stdio mode with selfhosted-supabase-mcp
# Or set to HTTP URL if running MCP server in HTTP mode
SUPABASE_MCP_URL=

# Direct DB connection (optional, for privileged MCP operations)
# SUPABASE_DB_URL=postgresql://postgres:<password>@<host>:5432/postgres

# Returns A2A (internal, supervisord handles this)
RETURNS_A2A_URL=http://localhost:8001
```

### 3.2 — How MCP Connection Works

The file `apps/support_root/tools_supabase.py` auto-detects the connection mode:

- **If `SUPABASE_MCP_URL` is empty** → Uses **stdio mode**: runs `npx -y selfhosted-supabase-mcp` as a child process. This requires Node.js and npm available in the container (already in the Dockerfile). The MCP server connects to Supabase using `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY`.

- **If `SUPABASE_MCP_URL` starts with `http://` or `https://`** → Uses **HTTP mode**: connects to a running MCP server via `StreamableHTTPConnectionParams`. Use this if you run the MCP server separately.

**Recommended for Docker deployment: leave `SUPABASE_MCP_URL` empty (stdio mode).** The Dockerfile includes Node.js for npx.

---

## Phase 4: Test Locally

### 4.1 — Install Dependencies

```bash
cd week3/assignment-1/nexus
pip install -r requirements.txt
```

### 4.2 — Start Returns A2A Service

```bash
# Terminal 1: Start the A2A returns service
cd week3/assignment-1/nexus
SUPABASE_URL=<url> SUPABASE_ANON_KEY=<key> \
uvicorn apps.returns_a2a.agent:a2a_app --host 0.0.0.0 --port 8001
```

Verify it's running:
```bash
curl -s http://localhost:8001/.well-known/agent-card.json | python3 -m json.tool
# Should return the agent card JSON
```

### 4.3 — Start Main Application

```bash
# Terminal 2: Start the main Nexus app
cd week3/assignment-1/nexus
GOOGLE_API_KEY=<key> SUPABASE_URL=<url> SUPABASE_ANON_KEY=<key> SUPABASE_SERVICE_ROLE_KEY=<key> \
uvicorn main:app --host 0.0.0.0 --port 8003
```

### 4.4 — Verify

```bash
# Health check
curl http://localhost:8003/health
# → {"status":"healthy","service":"nexus-week3"}

# Open web UI
open http://localhost:8003
```

### 4.5 — Test All 3 Scenarios in the Chat Tab

1. **Billing test**: Type or click the example chip:
   > "Hi, I was charged twice for my last order. My email is customer3@example.com. Can you check my recent orders and tell me what happened?"

   **Expected**: Routes to `billing_agent`, makes MCP/SQL queries, finds orders 4 and 5 (duplicate $129.99 charges).

2. **Returns test**: Type or click the example chip:
   > "I want to return order 3 because it arrived with a scratched case. Am I eligible and can you start the return?"

   **Expected**: Routes to `returns_agent` (via A2A), calls `check_return_eligibility(3)`, finds it eligible, calls `initiate_return(3, "scratched case")`, returns RMA number.

3. **Escalation test**: Type or click the example chip:
   > "This is unacceptable. I've been waiting THREE WEEKS for my refund on the AI Training Credits and nobody is helping me. I want a manager NOW."

   **Expected**: Routes to `escalation_agent`, looks up tickets, creates/updates ticket with status='escalated' and priority='urgent'.

### 4.6 — Test Autoplay (Results Tab)

Click the **"Results"** tab, then click **"Run All Scenarios"**. This runs all 3 test scenarios sequentially and shows routing accuracy.

### 4.7 — Test ADK Dev UI (for Demo Recording)

```bash
cd week3/assignment-1/nexus/apps/support_root
adk web
# Opens ADK's built-in dev UI at http://localhost:8000
```

---

## Phase 5: Deploy via Docker

### 5.1 — How the Docker Setup Works

The `docker-compose.yml` has a `week3-nexus` service:
- Builds from `week3/assignment-1/nexus/Dockerfile`
- Reads `.env` from repo root
- Sets `BASE_PATH=/week3/nexus` and `RETURNS_A2A_URL=http://localhost:8001`
- Exposes port 8003 internally
- nginx proxies `/week3/nexus/` → `http://week3-nexus:8003/`

The Dockerfile:
- Python 3.12 + Node.js + npm + supervisor
- Installs pip requirements
- Copies the nexus directory
- Uses supervisord to run:
  - `returns_a2a` on port 8001 (priority 10, starts first)
  - `main_app` on port 8003 (priority 20, starts after)

### 5.2 — Build and Deploy

```bash
# From repo root on VPS
cd /path/to/The-AI-Internship

# Build and start just the nexus service first to test
docker compose build week3-nexus
docker compose up week3-nexus -d

# Check logs
docker compose logs week3-nexus -f

# Verify health
curl http://localhost:8003/health
```

### 5.3 — Deploy Everything

```bash
# Full deployment (nginx + all week services)
docker compose up --build -d

# Verify nginx is routing correctly
curl -s https://theaiinternship.ayushojha.com/week3/nexus/health
# → {"status":"healthy","service":"nexus-week3"}
```

### 5.4 — Troubleshooting

**"Connection refused" on port 8001 (A2A)**:
The returns A2A runs inside the same container on localhost:8001. Check supervisord logs:
```bash
docker compose exec week3-nexus supervisorctl status
# Both programs should show RUNNING
```

**MCP "npx not found"**:
The Dockerfile installs nodejs and npm. If using stdio mode, verify Node is available:
```bash
docker compose exec week3-nexus node --version
docker compose exec week3-nexus npx --version
```

**"selfhosted-supabase-mcp" fails to start**:
First run will download the package. Check npm registry access from the container:
```bash
docker compose exec week3-nexus npx -y selfhosted-supabase-mcp --help
```

**Supabase REST API returns empty/403**:
- Check that RLS is disabled or policies are in place (Phase 2.6)
- Verify `SUPABASE_ANON_KEY` is correct
- Test directly: `curl -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/rest/v1/customers?select=id"`

**Agent doesn't route correctly**:
- Check `GOOGLE_API_KEY` is valid
- Check that the Gemini model `gemini-2.5-flash` is accessible with your key
- Try running `adk web` locally to test in the ADK Dev UI

---

## Phase 6: Verify Production Deployment

### 6.1 — Endpoint Checks

```bash
BASE="https://theaiinternship.ayushojha.com/week3/nexus"

# Health
curl -s "$BASE/health"

# Architecture diagram
curl -s "$BASE/api/nexus/architecture" | python3 -m json.tool

# Chat (non-streaming)
curl -s -X POST "$BASE/api/nexus/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the orders for customer3@example.com?"}' | python3 -m json.tool

# SSE stream test
curl -N "$BASE/api/nexus/chat/stream?message=Hello"
```

### 6.2 — Web UI Verification

Open `https://theaiinternship.ayushojha.com/week3/nexus/` in a browser:

1. **Chat tab**: Send each of the 3 example prompts. Verify:
   - Agent badge updates (shows "Billing", "Returns", or "Escalation")
   - Activity log shows tool calls
   - Response renders as markdown

2. **Architecture tab**: Mermaid diagram loads and shows the agent topology

3. **Results tab**: Click "Run All Scenarios". Verify:
   - Progress bar advances through 3 scenarios
   - Each phase dot turns green (pass) or red (fail)
   - Routing accuracy shows (target: 100% = 3/3)
   - Download ZIP button works

### 6.3 — Landing Page

Open `https://theaiinternship.ayushojha.com/`:
- Week 3 in timeline should show emerald checkmark (not gray schedule icon)
- Week 3 card should appear with "Nexus Multi-Agent" title and "Live" badge
- "Launch App" button should link to `/week3/nexus/`
- Hero section should have "Week 3: Multi-Agent" button

---

## Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `apps/support_root/agent.py` | Root router + billing + escalation agents |
| `apps/support_root/tools_supabase.py` | MCP connection factory (stdio/HTTP) |
| `apps/returns_a2a/agent.py` | Returns A2A service (`to_a2a()` on port 8001) |
| `apps/returns_a2a/tools.py` | Return eligibility + initiation (Supabase REST) |
| `agent_runner.py` | FastAPI ↔ ADK bridge (event parsing) |
| `router.py` | API routes: /chat, /stream, /autoplay, /results |
| `main.py` | FastAPI entrypoint + static file serving |
| `config.py` | Environment variable loading |
| `db/schema.sql` | 3 tables: customers, orders, support_tickets |
| `db/seed.sql` | 5 customers, 12 orders, 8 tickets |
| `Dockerfile` | Python 3.12 + Node.js + supervisord |
| `supervisord.conf` | Runs A2A (8001) + main app (8003) |
| `docker-compose.yml` | `week3-nexus` service definition |
| `gateway/nginx.conf` | `/week3/nexus/` → `week3-nexus:8003` proxy |

## Environment Variables Quick Copy

```bash
GOOGLE_API_KEY=
GOOGLE_GENAI_USE_VERTEXAI=FALSE
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_MCP_URL=
RETURNS_A2A_URL=http://localhost:8001
BASE_PATH=/week3/nexus
```
