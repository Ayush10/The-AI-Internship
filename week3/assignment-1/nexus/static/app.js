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
    if (window._mermaidRendered) renderArchitecture();
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
    if (name === "architecture" && !window._mermaidRendered) renderArchitecture();
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
    badge.classList.add("flex");

    const map = {
        billing_agent: { label: "Billing", cls: "agent-badge-billing", color: "#2563eb" },
        returns_agent: { label: "Returns", cls: "agent-badge-returns", color: "#7c3aed" },
        escalation_agent: { label: "Escalation", cls: "agent-badge-escalation", color: "#ef4444" },
        nexus_support_router: { label: "Router", cls: "agent-badge-router", color: "#059669" },
    };

    const info = map[agent] || { label: agent || "Idle", cls: "agent-badge-idle", color: "#9ca3af" };

    badge.className = `flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold border ${info.cls}`;
    dot.style.background = info.color;
    dot.classList.toggle("animate-pulse-dot", active);
    text.textContent = info.label;
    currentAgent = agent;
}

// ── Activity Log ─────────────────────────────────────────────────────
function addActivity(event) {
    const log = document.getElementById("activity-log");
    if (!log) return;

    // Clear placeholder
    if (log.querySelector("p")) log.innerHTML = "";

    const item = document.createElement("div");
    item.className = "activity-item animate-slide-in";

    if (event.type === "routing") {
        item.classList.add("activity-routing");
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-primary text-xs">route</span><span class="font-semibold text-primary">Routed to ${escapeHtml(event.agent)}</span></div>`;
    } else if (event.type === "tool_call") {
        item.classList.add("activity-tool");
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-mcp text-xs">build</span><span class="font-semibold text-mcp">${escapeHtml(event.tool)}</span></div>
            <div class="mt-1 text-[10px] text-muted-light dark:text-muted-dark font-mono truncate">${escapeHtml(JSON.stringify(event.args || {}).slice(0, 120))}</div>`;
    } else if (event.type === "tool_result") {
        item.classList.add("activity-tool-result");
        const preview = typeof event.result === "string" ? event.result.slice(0, 100) : JSON.stringify(event.result || "").slice(0, 100);
        item.innerHTML = `<div class="flex items-center gap-2"><span class="material-icons-round text-amber-500 text-xs">check_circle</span><span class="font-semibold text-amber-600 dark:text-amber-400">Tool Result</span></div>
            <div class="mt-1 text-[10px] text-muted-light dark:text-muted-dark font-mono truncate">${escapeHtml(preview)}</div>`;
    }

    log.appendChild(item);
    scrollToBottom(log);
}

// ── Chat Bubbles ─────────────────────────────────────────────────────
function addMessage(role, content, agent) {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    // Hide welcome placeholder
    const placeholder = container.querySelector(".text-center.py-12");
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
        tag.className = "text-[10px] mt-2 text-muted-light dark:text-muted-dark flex items-center gap-1";
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
    bubble.innerHTML = `<span class="inline-flex gap-1"><span class="w-2 h-2 bg-primary rounded-full animate-pulse-dot"></span><span class="w-2 h-2 bg-primary rounded-full animate-pulse-dot" style="animation-delay:0.2s"></span><span class="w-2 h-2 bg-primary rounded-full animate-pulse-dot" style="animation-delay:0.4s"></span></span>`;

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

async function sendMessage(message) {
    isProcessing = true;
    const sendBtn = document.getElementById("send-btn");
    sendBtn.disabled = true;

    // Hide example prompts after first message
    const examples = document.getElementById("example-prompts");
    if (examples && messages.length === 0) examples.classList.add("hidden");

    addMessage("user", message);
    setAgentBadge("nexus_support_router", true);

    // Clear previous activity
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
}

// ── Architecture ─────────────────────────────────────────────────────
async function renderArchitecture() {
    const container = document.getElementById("mermaid-diagram");
    if (!container) return;

    try {
        const resp = await fetch(callAPI("/api/nexus/architecture"));
        const data = await resp.json();

        const isDark = document.documentElement.classList.contains("dark");
        mermaid.initialize({
            startOnLoad: false,
            theme: isDark ? "dark" : "default",
            securityLevel: "loose",
            flowchart: { useMaxWidth: true, htmlLabels: true, curve: "basis" },
        });

        container.innerHTML = "";
        const { svg } = await mermaid.render("nexus-arch", data.mermaid);
        container.innerHTML = `<div class="mermaid-container">${svg}</div>`;
        window._mermaidRendered = true;
    } catch (err) {
        container.innerHTML = `<p class="text-sm text-red-500">Failed to load architecture: ${escapeHtml(err.message)}</p>`;
    }
}

// ── Autoplay ─────────────────────────────────────────────────────────
async function runAutoplay() {
    if (autoplayRunning) return;
    autoplayRunning = true;

    const btn = document.getElementById("autoplay-btn");
    const progress = document.getElementById("autoplay-progress");
    const bar = document.getElementById("autoplay-bar");
    const status = document.getElementById("autoplay-status");
    const dots = document.getElementById("phase-dots");
    const resultsContainer = document.getElementById("results-container");

    btn.disabled = true;
    btn.innerHTML = `<span class="material-icons-round text-sm animate-spin">refresh</span>Running...`;
    progress.classList.remove("hidden");
    resultsContainer.classList.add("hidden");
    bar.style.width = "0%";
    dots.innerHTML = "";

    let totalScenarios = 3;
    let completedScenarios = 0;
    const scenarioData = [];

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
                    for (let i = 0; i < totalScenarios; i++) {
                        const dot = document.createElement("span");
                        dot.className = "w-3 h-3 rounded-full bg-gray-300 dark:bg-white/10 transition-colors";
                        dot.id = `phase-dot-${i}`;
                        dots.appendChild(dot);
                    }
                    status.textContent = "Starting scenarios...";
                } else if (data.type === "scenario_start") {
                    status.textContent = `Running: ${data.name}`;
                    const dot = document.getElementById(`phase-dot-${data.index}`);
                    if (dot) dot.className = "w-3 h-3 rounded-full bg-primary animate-pulse-dot transition-colors";
                    bar.style.width = `${((data.index) / totalScenarios) * 100}%`;
                } else if (data.type === "scenario_complete") {
                    completedScenarios++;
                    const dot = document.getElementById(`phase-dot-${data.index}`);
                    if (dot) {
                        dot.classList.remove("animate-pulse-dot");
                        dot.className = data.routing_correct
                            ? "w-3 h-3 rounded-full bg-primary transition-colors"
                            : "w-3 h-3 rounded-full bg-red-500 transition-colors";
                    }
                    bar.style.width = `${(completedScenarios / totalScenarios) * 100}%`;
                    scenarioData.push(data);
                } else if (data.type === "autoplay_complete") {
                    status.textContent = `Complete — ${Math.round(data.routing_accuracy * 100)}% routing accuracy`;
                    showResults(data.routing_accuracy, scenarioData);
                } else if (data.type === "done") {
                    break;
                }
            }
        }
    } catch (err) {
        status.textContent = `Error: ${err.message}`;
    }

    btn.disabled = false;
    btn.innerHTML = `<span class="material-icons-round text-sm">rocket_launch</span>Run All Scenarios`;
    autoplayRunning = false;
}

function showResults(accuracy, scenarios) {
    const container = document.getElementById("results-container");
    const accuracyDisplay = document.getElementById("accuracy-display");
    const scenarioResults = document.getElementById("scenario-results");

    container.classList.remove("hidden");
    accuracyDisplay.textContent = `${Math.round(accuracy * 100)}%`;

    const names = { billing: "Billing Inquiry (MCP)", returns: "Return Request (A2A)", escalation: "Escalation (Angry Customer)" };
    const icons = { billing: "receipt_long", returns: "assignment_return", escalation: "warning" };
    const colors = { billing_agent: "mcp", returns_agent: "a2a", escalation_agent: "red-500" };

    scenarioResults.innerHTML = scenarios.map((s, i) => {
        const pass = s.routing_correct;
        const scenarioId = ["billing", "returns", "escalation"][i] || "billing";
        const icon = icons[scenarioId] || "help";
        const color = colors[s.actual_agent] || "gray-500";

        return `<div class="scenario-card ${pass ? "scenario-pass" : "scenario-fail"} bg-card-light dark:bg-card-dark">
            <div class="px-5 py-4 flex items-center justify-between border-b border-border-light dark:border-border-dark">
                <div class="flex items-center gap-3">
                    <span class="material-icons-round text-${color}">${icon}</span>
                    <div>
                        <h4 class="text-sm font-bold">${names[scenarioId] || `Scenario ${i + 1}`}</h4>
                        <p class="text-[10px] text-muted-light dark:text-muted-dark">Agent: ${escapeHtml(s.actual_agent || "unknown")} | Tools: ${s.tool_call_count || 0}</p>
                    </div>
                </div>
                <span class="material-icons-round ${pass ? "text-primary" : "text-red-500"}">${pass ? "check_circle" : "cancel"}</span>
            </div>
        </div>`;
    }).join("");
}

// ── Download ─────────────────────────────────────────────────────────
function downloadResults() {
    window.location.href = callAPI("/api/nexus/download/zip");
}

// ── Marked Config ────────────────────────────────────────────────────
if (typeof marked !== "undefined") {
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
}

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    applyTheme();
});
