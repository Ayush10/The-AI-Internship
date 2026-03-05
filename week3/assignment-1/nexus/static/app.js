/* Nexus — Multi-Agent Support UI */

const BASE = window.__BASE_PATH__ || "";

// ── State ────────────────────────────────────────────────────────────
let activeTab = "chat";
let sessionId = null;
let isProcessing = false;
let currentAgent = null;
let messages = [];
let autoplayRunning = false;

// ── Theme ────────────────────────────────────────────────────────────
function applyTheme() {
    const stored = localStorage.getItem("nexus-theme");
    const dark = stored ? stored === "dark" : true;
    document.documentElement.classList.toggle("dark", dark);
    const icon = document.getElementById("theme-icon");
    if (icon) icon.textContent = dark ? "light_mode" : "dark_mode";
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains("dark");
    localStorage.setItem("nexus-theme", isDark ? "light" : "dark");
    applyTheme();
    // Architecture is custom HTML, auto-adapts via CSS dark mode
}

applyTheme();

// ── Tabs ─────────────────────────────────────────────────────────────
function switchTab(name) {
    activeTab = name;
    ["chat", "architecture", "results"].forEach((t) => {
        const panel = document.getElementById(`panel-${t}`);
        const tab = document.getElementById(`tab-${t}`);
        const mtab = document.getElementById(`mtab-${t}`);
        if (panel) panel.classList.toggle("hidden", t !== name);
        [tab, mtab].forEach((btn) => {
            if (!btn) return;
            btn.classList.toggle("tab-active", t === name);
        });
    });
    // Architecture is now custom HTML, no dynamic rendering needed
}

// ── Helpers ──────────────────────────────────────────────────────────
function callAPI(path) {
    return `${BASE}${path}`;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom(el) {
    requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

// ── Agent Badge ──────────────────────────────────────────────────────
function setAgentBadge(agent, active) {
    const badge = document.getElementById("agent-badge");
    const dot = document.getElementById("agent-badge-dot");
    const text = document.getElementById("agent-badge-text");
    if (!badge) return;

    badge.classList.remove("hidden");

    const map = {
        billing_agent: { label: "Billing", cls: "agent-badge-billing" },
        returns_agent: { label: "Returns", cls: "agent-badge-returns" },
        escalation_agent: { label: "Escalation", cls: "agent-badge-escalation" },
        nexus_support_router: { label: "Router", cls: "agent-badge-router" },
    };

    const info = map[agent] || { label: agent || "Idle", cls: "agent-badge-idle" };

    badge.className = `agent-badge ${info.cls}`;
    dot.classList.toggle("animate-pulse-dot", active);
    text.textContent = info.label;
    currentAgent = agent;
}

function getAgentTagClass(agent) {
    if (agent?.includes("billing")) return "agent-tag-billing";
    if (agent?.includes("returns")) return "agent-tag-returns";
    if (agent?.includes("escalation")) return "agent-tag-escalation";
    return "agent-tag-router";
}

// ── Activity Log ─────────────────────────────────────────────────────
function addActivity(event) {
    const log = document.getElementById("activity-log");
    if (!log) return;

    // Clear empty state
    const empty = log.querySelector(".activity-empty");
    if (empty) empty.remove();

    const item = document.createElement("div");
    item.className = "activity-item animate-slide-in";

    if (event.type === "routing") {
        item.classList.add("activity-routing");
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-primary text-xs">route</span><span class="font-semibold text-primary">Routed → ${escapeHtml(event.agent)}</span></div>`;
    } else if (event.type === "tool_call") {
        item.classList.add("activity-tool");
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-mcp text-xs">build</span><span class="font-semibold text-mcp">${escapeHtml(event.tool)}</span></div>
            <div class="mt-1 text-[10px] text-muted-light dark:text-muted-dark font-mono truncate">${escapeHtml(JSON.stringify(event.args || {}).slice(0, 120))}</div>`;
    } else if (event.type === "tool_result") {
        item.classList.add("activity-tool-result");
        const preview = typeof event.result === "string" ? event.result.slice(0, 100) : JSON.stringify(event.result || "").slice(0, 100);
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-amber-500 text-xs">check_circle</span><span class="font-semibold text-amber-600 dark:text-amber-400">Result</span></div>
            <div class="mt-1 text-[10px] text-muted-light dark:text-muted-dark font-mono truncate">${escapeHtml(preview)}</div>`;
    }

    log.appendChild(item);
    scrollToBottom(log);
}

// ── Chat Bubbles ─────────────────────────────────────────────────────
function addMessage(role, content, agent) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    const placeholder = container.querySelector(".welcome-hero");
    if (placeholder) placeholder.remove();

    const wrapper = document.createElement("div");
    wrapper.className = `flex ${role === "user" ? "justify-end" : "justify-start"} animate-fade-up`;

    const bubble = document.createElement("div");
    bubble.className = role === "user" ? "bubble-user" : "bubble-assistant";

    if (role === "user") {
        bubble.textContent = content;
    } else {
        bubble.innerHTML = marked.parse(content || "");
    }

    if (role === "assistant" && agent) {
        const tag = document.createElement("div");
        tag.className = `agent-tag ${getAgentTagClass(agent)}`;
        tag.innerHTML = `<span class="material-icons-round" style="font-size:10px">smart_toy</span>${escapeHtml(agent)}`;
        bubble.appendChild(tag);
    }

    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    scrollToBottom(container);
    messages.push({ role, content, agent });
}

function addStreamingBubble() {
    const container = document.getElementById("chat-messages");
    const wrapper = document.createElement("div");
    wrapper.className = "flex justify-start animate-fade-up";
    wrapper.id = "streaming-bubble";

    const bubble = document.createElement("div");
    bubble.className = "bubble-assistant";
    bubble.innerHTML = `<span class="inline-flex gap-1.5 py-1"><span class="w-2 h-2 bg-primary rounded-full animate-pulse-dot"></span><span class="w-2 h-2 bg-accent rounded-full animate-pulse-dot" style="animation-delay:0.2s"></span><span class="w-2 h-2 bg-mcp rounded-full animate-pulse-dot" style="animation-delay:0.4s"></span></span>`;

    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    scrollToBottom(container);
    return bubble;
}

function updateStreamingBubble(bubble, content) {
    if (!bubble) return;
    bubble.innerHTML = marked.parse(content);
    scrollToBottom(document.getElementById("chat-messages"));
}

function finalizeStreamingBubble(bubble, content, agent) {
    const wrapper = document.getElementById("streaming-bubble");
    if (wrapper) wrapper.remove();
    addMessage("assistant", content, agent);
}

// ── Chat Send ────────────────────────────────────────────────────────
function handleSend(e) {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg || isProcessing) return;
    input.value = "";
    updateSendBtn();
    sendMessage(msg);
}

function sendExample(type) {
    if (isProcessing) return;
    const examples = {
        billing: "Hi, I was charged twice for my last order. My email is customer3@example.com. Can you check my recent orders and tell me what happened?",
        returns: "I want to return order 3 because it arrived with a scratched case. Am I eligible and can you start the return?",
        escalation: "This is unacceptable. I've been waiting THREE WEEKS for my refund on the AI Training Credits and nobody is helping me. I want a manager NOW.",
    };
    const msg = examples[type];
    if (msg) {
        document.getElementById("chat-input").value = "";
        sendMessage(msg);
    }
}

function updateSendBtn() {
    const input = document.getElementById("chat-input");
    const btn = document.getElementById("send-btn");
    if (btn) btn.disabled = !input.value.trim() || isProcessing;
}

async function sendMessage(message) {
    isProcessing = true;
    const sendBtn = document.getElementById("send-btn");
    sendBtn.disabled = true;

    const examples = document.getElementById("example-prompts");
    if (examples && messages.length === 0) {
        examples.style.opacity = "0";
        examples.style.transform = "translateY(8px)";
        examples.style.transition = "all 0.3s";
        setTimeout(() => examples.classList.add("hidden"), 300);
    }

    addMessage("user", message);
    setAgentBadge("nexus_support_router", true);

    // Clear activity
    const log = document.getElementById("activity-log");
    if (log) log.innerHTML = "";

    const bubble = addStreamingBubble();
    let streamedText = "";
    let finalAgent = "nexus_support_router";

    try {
        const params = new URLSearchParams({ message });
        if (sessionId) params.set("session_id", sessionId);

        const resp = await fetch(callAPI(`/api/nexus/chat/stream?${params}`));
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                let data;
                try { data = JSON.parse(line.slice(6)); } catch { continue; }

                if (data.type === "session") {
                    sessionId = data.session_id;
                } else if (data.type === "routing") {
                    setAgentBadge(data.agent, true);
                    addActivity(data);
                } else if (data.type === "tool_call") {
                    addActivity(data);
                } else if (data.type === "tool_result") {
                    addActivity(data);
                } else if (data.type === "text") {
                    streamedText = data.content || "";
                    updateStreamingBubble(bubble, streamedText);
                    if (data.agent) finalAgent = data.agent;
                } else if (data.type === "final") {
                    streamedText = data.content || streamedText;
                    finalAgent = data.agent || finalAgent;
                } else if (data.type === "error") {
                    streamedText = `Error: ${data.content}`;
                } else if (data.type === "done") {
                    break;
                }
            }
        }
    } catch (err) {
        streamedText = streamedText || `Connection error: ${err.message}`;
    }

    finalizeStreamingBubble(bubble, streamedText, finalAgent);
    setAgentBadge(finalAgent, false);
    isProcessing = false;
    sendBtn.disabled = false;
    updateSendBtn();
}

// ── Architecture (Interactive) ───────────────────────────────────────
const archNodeData = {
    customer: {
        name: "Customer",
        icon: "person",
        color: "#52525b",
        type: "User Input",
        description: "The end-user submitting support requests. Messages are routed to the appropriate specialist agent based on intent detection.",
        details: [
            { label: "Input", value: "Natural language support queries" },
            { label: "Channel", value: "Web UI chat interface" },
            { label: "Session", value: "Persistent via InMemorySessionService" },
        ],
        connections: ["Root Router Agent"],
    },
    router: {
        name: "Root Router Agent",
        icon: "hub",
        color: "#10b981",
        type: "Router Agent",
        description: "The orchestrator that analyzes user intent and delegates to the correct specialist sub-agent. Uses Gemini 2.5 Flash for classification.",
        details: [
            { label: "Model", value: "Gemini 2.5 Flash" },
            { label: "Framework", value: "Google ADK Agent" },
            { label: "Sub-agents", value: "3 (Billing, Returns, Escalation)" },
            { label: "Routing", value: "Intent-based classification" },
        ],
        connections: ["Billing Agent", "Returns Agent", "Escalation Agent"],
    },
    billing: {
        name: "Billing Agent",
        icon: "receipt_long",
        color: "#3b82f6",
        type: "MCP Sub-Agent",
        description: "Handles billing inquiries, order lookups, and charge disputes. Connects to Supabase via MCP stdio for read-only database access.",
        details: [
            { label: "Model", value: "Gemini 2.5 Flash" },
            { label: "Protocol", value: "MCP (Model Context Protocol)" },
            { label: "Access", value: "Read-only (Supabase)" },
            { label: "Tables", value: "customers, orders" },
            { label: "MCP Server", value: "selfhosted-supabase-mcp (stdio)" },
        ],
        connections: ["Supabase PostgreSQL"],
    },
    returns: {
        name: "Returns Agent",
        icon: "assignment_return",
        color: "#8b5cf6",
        type: "A2A Sub-Agent",
        description: "Processes return requests by communicating with the Returns A2A microservice. Uses RemoteA2aAgent to delegate to the external service.",
        details: [
            { label: "Model", value: "Gemini 2.5 Flash" },
            { label: "Protocol", value: "A2A (Agent-to-Agent)" },
            { label: "Remote URL", value: "http://localhost:8001" },
            { label: "ADK Class", value: "RemoteA2aAgent" },
        ],
        connections: ["Returns A2A Service"],
    },
    escalation: {
        name: "Escalation Agent",
        icon: "warning",
        color: "#f43f5e",
        type: "MCP Sub-Agent",
        description: "Handles angry customers and urgent issues. Creates/updates support tickets with escalated priority via MCP read-write access.",
        details: [
            { label: "Model", value: "Gemini 2.5 Flash" },
            { label: "Protocol", value: "MCP (Model Context Protocol)" },
            { label: "Access", value: "Read-write (Supabase)" },
            { label: "Tables", value: "customers, orders, support_tickets" },
            { label: "Actions", value: "Create tickets, set priority: urgent" },
        ],
        connections: ["Supabase PostgreSQL"],
    },
    a2a_service: {
        name: "Returns A2A Service",
        icon: "dns",
        color: "#7c3aed",
        type: "Microservice",
        description: "Standalone FastAPI service running on port 8001, exposed via ADK's to_a2a(). Hosts the Returns agent with two tools for eligibility checks and return initiation.",
        details: [
            { label: "Port", value: "8001" },
            { label: "Framework", value: "Google ADK to_a2a()" },
            { label: "Server", value: "Uvicorn (supervisord)" },
            { label: "Tools", value: "check_return_eligibility, initiate_return" },
            { label: "API", value: "Supabase REST (PostgREST)" },
        ],
        connections: ["check_return_eligibility", "initiate_return"],
    },
    check_elig: {
        name: "check_return_eligibility",
        icon: "fact_check",
        color: "#64748b",
        type: "Tool Function",
        description: "Checks if an order is eligible for return. Queries order status, delivery date, and calculates 30-day return window.",
        details: [
            { label: "Input", value: "order_id: int" },
            { label: "Output", value: "{eligible, reason, return_by_date}" },
            { label: "Logic", value: "status=delivered AND within 30 days" },
            { label: "API", value: "GET /rest/v1/orders?id=eq.{id}" },
        ],
        connections: ["Supabase PostgreSQL"],
    },
    init_return: {
        name: "initiate_return",
        icon: "undo",
        color: "#64748b",
        type: "Tool Function",
        description: "Processes a return by validating eligibility, generating an RMA number, and updating the order status to 'returned' in the database.",
        details: [
            { label: "Input", value: "order_id: int, reason: str" },
            { label: "Output", value: "{rma_id, status, instructions}" },
            { label: "Action", value: "PATCH order status \u2192 returned" },
            { label: "API", value: "PATCH /rest/v1/orders?id=eq.{id}" },
        ],
        connections: ["Supabase PostgreSQL"],
    },
    database: {
        name: "Supabase PostgreSQL",
        icon: "storage",
        color: "#f59e0b",
        type: "Database",
        description: "Self-hosted Supabase instance on VPS (Coolify). Contains 3 tables with seeded demo data for realistic customer support scenarios.",
        details: [
            { label: "Host", value: "Self-hosted via Coolify" },
            { label: "Tables", value: "customers (5), orders (12), support_tickets (8)" },
            { label: "Access: MCP", value: "stdio via selfhosted-supabase-mcp" },
            { label: "Access: REST", value: "PostgREST API (httpx)" },
            { label: "Auth", value: "Anon key + Service role key" },
        ],
        connections: [],
    },
};

let selectedArchNode = null;

function selectArchNode(nodeId) {
    const data = archNodeData[nodeId];
    if (!data) return;

    // Highlight selected node
    document.querySelectorAll(".arch-node").forEach(el => el.classList.remove("arch-node-selected"));
    const nodeEl = document.querySelector(`[data-node="${nodeId}"]`);
    if (nodeEl) nodeEl.classList.add("arch-node-selected");
    selectedArchNode = nodeId;

    // Populate inspector
    const empty = document.getElementById("arch-inspector-empty");
    const detail = document.getElementById("arch-inspector-detail");
    if (empty) empty.classList.add("hidden");
    if (!detail) return;
    detail.classList.remove("hidden");

    const detailRows = data.details.map(d =>
        `<div class="inspector-row">
            <span class="inspector-key">${escapeHtml(d.label)}</span>
            <span class="inspector-val">${escapeHtml(d.value)}</span>
        </div>`
    ).join("");

    const connList = data.connections.length > 0
        ? data.connections.map(c => `<span class="inspector-conn">${escapeHtml(c)}</span>`).join("")
        : `<span class="text-[10px] text-muted-light dark:text-muted-dark italic">None</span>`;

    detail.innerHTML = `
        <div class="inspector-header">
            <div class="inspector-icon" style="background:${data.color}">
                <span class="material-icons-round text-white">${data.icon}</span>
            </div>
            <div>
                <h3 class="text-base font-extrabold">${escapeHtml(data.name)}</h3>
                <span class="inspector-type">${escapeHtml(data.type)}</span>
            </div>
        </div>
        <p class="inspector-desc">${escapeHtml(data.description)}</p>
        <div class="inspector-section">
            <h4 class="inspector-section-title">Configuration</h4>
            ${detailRows}
        </div>
        <div class="inspector-section">
            <h4 class="inspector-section-title">Connections</h4>
            <div class="flex flex-wrap gap-1.5">${connList}</div>
        </div>
    `;
}

// ── Autoplay ─────────────────────────────────────────────────────────
let autoplayEventCount = 0;
let autoplayLogEntries = {};

function addLogEntry(scenarioIndex, event) {
    const log = document.getElementById("autoplay-log");
    if (!log) return;

    autoplayEventCount++;
    const countEl = document.getElementById("log-event-count");
    if (countEl) countEl.textContent = `${autoplayEventCount} events`;

    const ts = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const entry = document.createElement("div");
    entry.className = "log-entry animate-slide-in";

    let icon, color, label, detail = "";

    const et = event.event_type || event.type;

    if (et === "routing") {
        icon = "route"; color = "primary"; label = "Routed";
        detail = `\u2192 ${event.agent || "unknown"}`;
    } else if (et === "tool_call") {
        icon = "build"; color = "mcp"; label = event.tool || "Tool Call";
        const argStr = JSON.stringify(event.args || {});
        detail = argStr.length > 80 ? argStr.slice(0, 80) + "\u2026" : argStr;
    } else if (et === "tool_result") {
        icon = "check_circle"; color = "amber-500"; label = "Result";
        const res = typeof event.result === "string" ? event.result : JSON.stringify(event.result || "");
        detail = res.length > 80 ? res.slice(0, 80) + "\u2026" : res;
    } else if (et === "text") {
        icon = "chat_bubble"; color = "primary"; label = "Streaming";
        detail = (event.content || "").slice(0, 60) + ((event.content || "").length > 60 ? "\u2026" : "");
    } else if (et === "final") {
        icon = "task_alt"; color = "primary"; label = "Complete";
        detail = `Agent: ${event.agent || "unknown"}`;
    } else {
        return;
    }

    const scenarioLabels = ["Billing", "Returns", "Escalation"];
    const scenarioColors = ["mcp", "accent", "danger"];
    const sc = scenarioColors[scenarioIndex] || "primary";
    const sl = scenarioLabels[scenarioIndex] || `#${scenarioIndex + 1}`;

    entry.innerHTML = `
        <span class="log-ts">${ts}</span>
        <span class="log-scenario-tag log-scenario-${sc}">${sl}</span>
        <span class="material-icons-round log-icon text-${color}" style="font-size:13px">${icon}</span>
        <span class="log-label">${escapeHtml(label)}</span>
        <span class="log-detail">${escapeHtml(detail)}</span>
    `;

    log.appendChild(entry);
    scrollToBottom(log);

    if (!autoplayLogEntries[scenarioIndex]) autoplayLogEntries[scenarioIndex] = [];
    autoplayLogEntries[scenarioIndex].push({ ts, icon, color, label, detail });
}

async function runAutoplay() {
    if (autoplayRunning) return;
    autoplayRunning = true;
    autoplayEventCount = 0;
    autoplayLogEntries = {};

    const btn = document.getElementById("autoplay-btn");
    const progress = document.getElementById("autoplay-progress");
    const bar = document.getElementById("autoplay-bar");
    const status = document.getElementById("autoplay-status");
    const dots = document.getElementById("phase-dots");
    const resultsContainer = document.getElementById("results-container");
    const emptyState = document.getElementById("results-empty");
    const logPanel = document.getElementById("autoplay-log-panel");
    const log = document.getElementById("autoplay-log");

    btn.disabled = true;
    btn.innerHTML = `<span class="material-icons-round text-sm animate-spin">refresh</span>Running...`;
    progress.classList.remove("hidden");
    logPanel.classList.remove("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    resultsContainer.classList.add("hidden");
    bar.style.width = "0%";
    dots.innerHTML = "";
    log.innerHTML = "";

    // Reset live dot
    const liveDot = document.getElementById("log-live-dot");
    if (liveDot) { liveDot.classList.add("animate-pulse-dot"); liveDot.style.background = ""; }

    let totalScenarios = 3;
    let completedScenarios = 0;
    const scenarioData = [];
    let currentScenarioIndex = 0;

    try {
        const resp = await fetch(callAPI("/api/nexus/autoplay"));
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                let data;
                try { data = JSON.parse(line.slice(6)); } catch { continue; }

                if (data.type === "autoplay_start") {
                    totalScenarios = data.total_scenarios;
                    const labels = ["Billing", "Returns", "Escalation"];
                    for (let i = 0; i < totalScenarios; i++) {
                        const dot = document.createElement("div");
                        dot.className = "phase-dot-item";
                        dot.id = `phase-dot-${i}`;
                        dot.innerHTML = `<span class="phase-dot-circle"></span><span class="phase-dot-label">${labels[i] || `#${i+1}`}</span>`;
                        dots.appendChild(dot);
                    }
                    status.textContent = "Initializing agent system...";

                } else if (data.type === "scenario_start") {
                    currentScenarioIndex = data.index;
                    status.textContent = `Running: ${data.name}`;
                    const dot = document.getElementById(`phase-dot-${data.index}`);
                    if (dot) dot.classList.add("phase-dot-active");
                    bar.style.width = `${((data.index) / totalScenarios) * 100}%`;

                    // Log separator
                    const sep = document.createElement("div");
                    sep.className = "log-separator";
                    sep.innerHTML = `<span class="log-separator-line"></span><span class="log-separator-text">${escapeHtml(data.name)}</span><span class="log-separator-line"></span>`;
                    log.appendChild(sep);
                    scrollToBottom(log);

                } else if (data.type === "scenario_event") {
                    addLogEntry(currentScenarioIndex, data);

                } else if (data.type === "scenario_complete") {
                    completedScenarios++;
                    const dot = document.getElementById(`phase-dot-${data.index}`);
                    if (dot) {
                        dot.classList.remove("phase-dot-active");
                        dot.classList.add(data.routing_correct ? "phase-dot-pass" : "phase-dot-fail");
                    }
                    bar.style.width = `${(completedScenarios / totalScenarios) * 100}%`;
                    scenarioData.push(data);

                } else if (data.type === "autoplay_complete") {
                    status.textContent = `Complete \u2014 ${Math.round(data.routing_accuracy * 100)}% routing accuracy`;
                    if (liveDot) { liveDot.classList.remove("animate-pulse-dot"); liveDot.style.background = "#10b981"; }
                    showResults(data.routing_accuracy, data.total_tool_calls, scenarioData);

                } else if (data.type === "done") {
                    break;
                }
            }
        }
    } catch (err) {
        status.textContent = `Error: ${err.message}`;
    }

    btn.disabled = false;
    btn.innerHTML = `<span class="material-icons-round text-sm">rocket_launch</span>Re-run Scenarios`;
    autoplayRunning = false;
}

function showResults(accuracy, totalTools, scenarios) {
    const container = document.getElementById("results-container");
    container.classList.remove("hidden");

    // Summary stats
    document.getElementById("accuracy-display").textContent = `${Math.round(accuracy * 100)}%`;
    document.getElementById("total-tools-display").textContent = totalTools || scenarios.reduce((s, d) => s + (d.tool_call_count || 0), 0);
    const uniqueAgents = new Set(scenarios.map(s => s.actual_agent).filter(Boolean));
    document.getElementById("agents-used-display").textContent = uniqueAgents.size;

    const scenarioResults = document.getElementById("scenario-results");

    const meta = [
        { id: "billing", name: "Billing Inquiry", proto: "MCP", icon: "receipt_long", color: "mcp", gradient: "from-blue-500 to-blue-600" },
        { id: "returns", name: "Return Request", proto: "A2A", icon: "assignment_return", color: "accent", gradient: "from-violet-500 to-purple-600" },
        { id: "escalation", name: "Escalation", proto: "MCP", icon: "warning", color: "danger", gradient: "from-rose-500 to-pink-600" },
    ];

    scenarioResults.innerHTML = scenarios.map((s, i) => {
        const pass = s.routing_correct;
        const m = meta[i] || meta[0];
        const toolNames = (s.tool_names || []).filter(Boolean);
        const responseText = s.response || "No response captured";
        const userMessage = s.message || "";

        const toolBadges = toolNames.length > 0
            ? toolNames.map(t => `<span class="result-tool-badge">${escapeHtml(t)}</span>`).join("")
            : `<span class="text-[10px] text-muted-light dark:text-muted-dark italic">No tool calls recorded</span>`;

        return `<div class="scenario-detail-card ${pass ? "scenario-detail-pass" : "scenario-detail-fail"} animate-fade-up" style="animation-delay:${i * 0.12}s">
            <div class="scenario-detail-header" onclick="toggleScenarioDetail(${i})">
                <div class="flex items-center gap-3 min-w-0">
                    <div class="scenario-icon-box bg-gradient-to-br ${m.gradient}">
                        <span class="material-icons-round text-white text-lg">${m.icon}</span>
                    </div>
                    <div class="min-w-0">
                        <h4 class="text-sm font-bold flex items-center gap-2">
                            ${m.name}
                            <span class="proto-pill-tiny proto-pill-tiny-${m.color}">${m.proto}</span>
                        </h4>
                        <div class="flex items-center gap-3 mt-0.5">
                            <span class="text-[10px]">
                                <span class="font-semibold ${pass ? "text-primary" : "text-danger"}">${escapeHtml(s.actual_agent || "unknown")}</span>
                            </span>
                            <span class="text-[10px] text-muted-light dark:text-muted-dark">${s.tool_call_count || 0} tool calls</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                    <span class="scenario-result-badge ${pass ? "scenario-result-pass" : "scenario-result-fail"}">
                        <span class="material-icons-round" style="font-size:14px">${pass ? "check_circle" : "cancel"}</span>
                        ${pass ? "PASS" : "FAIL"}
                    </span>
                    <span class="material-icons-round text-muted-light dark:text-muted-dark text-lg scenario-chevron" id="chevron-${i}">expand_more</span>
                </div>
            </div>
            <div class="scenario-detail-body hidden" id="scenario-body-${i}">
                <div class="scenario-section">
                    <div class="scenario-section-label"><span class="material-icons-round" style="font-size:12px">person</span> User Query</div>
                    <div class="scenario-user-msg">${escapeHtml(userMessage)}</div>
                </div>
                <div class="scenario-section">
                    <div class="scenario-section-label"><span class="material-icons-round" style="font-size:12px">route</span> Routing</div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="routing-tag routing-expected">Expected: ${escapeHtml(s.expected_agent || "?")}</span>
                        <span class="material-icons-round text-muted-light dark:text-muted-dark" style="font-size:16px">arrow_forward</span>
                        <span class="routing-tag ${pass ? "routing-actual-pass" : "routing-actual-fail"}">Actual: ${escapeHtml(s.actual_agent || "?")}</span>
                    </div>
                </div>
                <div class="scenario-section">
                    <div class="scenario-section-label"><span class="material-icons-round" style="font-size:12px">build</span> Tool Calls (${toolNames.length})</div>
                    <div class="flex flex-wrap gap-1.5">${toolBadges}</div>
                </div>
                <div class="scenario-section">
                    <div class="scenario-section-label"><span class="material-icons-round" style="font-size:12px">smart_toy</span> Agent Response</div>
                    <div class="scenario-response">${marked.parse(responseText)}</div>
                </div>
            </div>
        </div>`;
    }).join("");
}

function toggleScenarioDetail(index) {
    const body = document.getElementById(`scenario-body-${index}`);
    const chevron = document.getElementById(`chevron-${index}`);
    if (!body) return;
    const isHidden = body.classList.contains("hidden");
    body.classList.toggle("hidden");
    if (chevron) chevron.textContent = isHidden ? "expand_less" : "expand_more";
}

// ── Download ─────────────────────────────────────────────────────────
function downloadResults() {
    window.location.href = callAPI("/api/nexus/download/zip");
}

// ── Marked Config ────────────────────────────────────────────────────
if (typeof marked !== "undefined") {
    marked.setOptions({ breaks: true, gfm: true });
}

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    applyTheme();

    const input = document.getElementById("chat-input");
    if (input) {
        input.addEventListener("input", updateSendBtn);
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                document.getElementById("chat-form").requestSubmit();
            }
        });
    }
});
