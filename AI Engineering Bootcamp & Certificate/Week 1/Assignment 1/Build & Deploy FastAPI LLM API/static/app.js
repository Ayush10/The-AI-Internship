const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const enhanceBtn = document.getElementById("enhance-btn");
const providerSelect = document.getElementById("provider");
const modeSelect = document.getElementById("mode");
const promptVersionSelect = document.getElementById("prompt-version");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");
const newChatBtn = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");
const sidebarEmpty = document.getElementById("sidebar-empty");

let isProcessing = false;
let currentConversationId = null;
let conversations = [];

// --- Event Listeners ---

sendBtn.addEventListener("click", handleSend);
enhanceBtn.addEventListener("click", handleEnhance);
newChatBtn.addEventListener("click", startNewChat);
sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("collapsed"));

userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});

// --- Init ---

loadConversations();

// --- Handlers ---

async function handleSend() {
    const text = userInput.value.trim();
    if (!text || isProcessing) return;

    const mode = modeSelect.value;
    const provider = providerSelect.value;
    const promptVersion = parseInt(promptVersionSelect.value);

    clearWelcome();
    addMessage("user", text);
    userInput.value = "";
    setProcessing(true);

    // Determine endpoint type
    let endpoint = "chat";
    if (mode === "summarize" && promptVersion > 0) endpoint = "summarize";
    else if (mode === "sentiment" && promptVersion > 0) endpoint = "sentiment";

    // Create conversation if needed
    if (!currentConversationId) {
        try {
            const convo = await callAPI("/api/conversations", {
                method: "POST",
                body: {
                    title: text.substring(0, 50),
                    endpoint,
                    mode,
                    provider,
                    prompt_version: promptVersion > 0 ? promptVersion : null,
                },
            });
            currentConversationId = convo.id;
            await loadConversations();
        } catch (err) {
            // Non-fatal — continue without history
            console.warn("Failed to create conversation:", err);
        }
    }

    const loadingEl = addLoadingMessage(provider);
    const convParam = currentConversationId ? { conversation_id: currentConversationId } : {};

    try {
        let result;

        if (endpoint === "summarize") {
            result = await callAPI("/summarize", {
                method: "POST",
                body: { text, max_length: 100 },
                params: { provider, prompt_version: promptVersion, ...convParam },
            });
            addMessage("assistant", result.summary, {
                provider: result.provider,
                meta: `Prompt v${result.prompt_version}`,
            });
        } else if (endpoint === "sentiment") {
            result = await callAPI("/analyze-sentiment", {
                method: "POST",
                body: { text },
                params: { provider, prompt_version: promptVersion, ...convParam },
            });
            const formatted =
                `Sentiment: ${result.sentiment}\n` +
                `Confidence: ${(result.confidence * 100).toFixed(1)}%\n` +
                `Explanation: ${result.explanation}`;
            addMessage("assistant", formatted, {
                provider: result.provider,
                meta: `Prompt v${result.prompt_version}`,
            });
        } else {
            result = await callAPI("/chat", {
                method: "POST",
                body: { message: text, provider, mode },
                params: convParam,
            });
            addMessage("assistant", result.response, {
                provider: result.provider,
            });
        }
    } catch (err) {
        addMessage("assistant", `Error: ${err.message}`, { isError: true });
    } finally {
        loadingEl.remove();
        setProcessing(false);
    }
}

async function handleEnhance() {
    const text = userInput.value.trim();
    if (!text || isProcessing) return;

    setProcessing(true);
    enhanceBtn.innerHTML = '<span class="enhance-icon">&#9889;</span> Enhancing<span class="loading-dots"></span>';

    try {
        const params = currentConversationId ? { conversation_id: currentConversationId } : {};
        const result = await callAPI("/enhance-prompt", {
            method: "POST",
            body: { prompt: text },
            params,
        });

        userInput.value = result.enhanced_prompt;
        userInput.focus();

        if (result.techniques_applied.length > 0) {
            clearWelcome();
            addSystemNote(
                `Prompt enhanced using: ${result.techniques_applied.join(", ")}`
            );
        }
    } catch (err) {
        addSystemNote(`Enhancement failed: ${err.message}`);
    } finally {
        enhanceBtn.innerHTML = '<span class="enhance-icon">&#9889;</span> Enhance';
        setProcessing(false);
    }
}

// --- Conversation Management ---

function startNewChat() {
    currentConversationId = null;
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <p>Choose a model and mode above, then start chatting.</p>
            <p>In <strong>Summarize</strong> mode, paste text to get a summary.<br>
               In <strong>Sentiment</strong> mode, paste text for sentiment analysis.<br>
               In <strong>General</strong> mode, just chat freely.</p>
        </div>`;
    highlightActive();
    userInput.focus();
}

async function loadConversations() {
    try {
        conversations = await callAPI("/api/conversations");
        renderSidebar();
    } catch (err) {
        console.warn("Failed to load conversations:", err);
    }
}

async function loadConversation(id) {
    try {
        const convo = await callAPI(`/api/conversations/${id}`);
        currentConversationId = convo.id;

        // Set controls to match conversation settings
        if (convo.provider) providerSelect.value = convo.provider;
        if (convo.mode) modeSelect.value = convo.mode;
        if (convo.prompt_version) promptVersionSelect.value = String(convo.prompt_version);

        // Render messages
        chatContainer.innerHTML = "";
        for (const msg of convo.messages) {
            if (msg.role === "user") {
                addMessage("user", msg.content);
            } else if (msg.role === "assistant") {
                addMessage("assistant", msg.content, { provider: convo.provider });
            }
        }

        if (convo.messages.length === 0) {
            chatContainer.innerHTML = `<div class="welcome-message"><p>This conversation is empty. Send a message to get started.</p></div>`;
        }

        highlightActive();

        // Collapse sidebar on mobile
        if (window.innerWidth <= 768) {
            sidebar.classList.add("collapsed");
        }
    } catch (err) {
        addSystemNote(`Failed to load conversation: ${err.message}`);
    }
}

async function deleteConversation(id, e) {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;

    try {
        await callAPI(`/api/conversations/${id}`, { method: "DELETE" });
        if (currentConversationId === id) {
            startNewChat();
        }
        await loadConversations();
    } catch (err) {
        console.warn("Failed to delete conversation:", err);
    }
}

function renderSidebar() {
    // Clear existing items but keep the empty state element
    const items = conversationList.querySelectorAll(".conversation-item");
    items.forEach((el) => el.remove());

    if (conversations.length === 0) {
        sidebarEmpty.style.display = "block";
        return;
    }

    sidebarEmpty.style.display = "none";

    for (const convo of conversations) {
        const el = document.createElement("div");
        el.className = `conversation-item${convo.id === currentConversationId ? " active" : ""}`;
        el.onclick = () => loadConversation(convo.id);

        const badgeClass = convo.endpoint === "chat" ? "chat"
            : convo.endpoint === "summarize" ? "summarize"
            : convo.endpoint === "sentiment" ? "sentiment"
            : "";

        el.innerHTML = `
            <div class="convo-title">${escapeHtml(convo.title)}</div>
            <div class="convo-meta">
                <span class="endpoint-badge ${badgeClass}">${convo.endpoint}</span>
                <span class="convo-time">${timeAgo(convo.updated_at)}</span>
            </div>
            <button class="convo-delete" title="Delete">&times;</button>
        `;

        el.querySelector(".convo-delete").onclick = (e) => deleteConversation(convo.id, e);
        conversationList.appendChild(el);
    }
}

function highlightActive() {
    conversationList.querySelectorAll(".conversation-item").forEach((el, i) => {
        el.classList.toggle("active", conversations[i] && conversations[i].id === currentConversationId);
    });
}

// --- API ---

async function callAPI(path, { method = "GET", body = null, params = {} } = {}) {
    const url = new URL(path, window.location.origin);
    for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) url.searchParams.set(k, v);
    }

    const options = { method, headers: {} };
    if (body) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const res = await fetch(url, options);

    if (res.status === 204) return null;

    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// --- DOM Helpers ---

function clearWelcome() {
    const welcome = chatContainer.querySelector(".welcome-message");
    if (welcome) welcome.remove();
}

function addMessage(role, text, options = {}) {
    const { provider, meta, isError, enhanced, techniques } = options;

    const msg = document.createElement("div");
    msg.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "You" : provider || "Assistant";
    if (enhanced) {
        label.innerHTML += ' <span class="enhanced-badge">Enhanced</span>';
    }

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    if (isError) bubble.style.color = "var(--error)";

    msg.appendChild(label);
    msg.appendChild(bubble);

    if (meta) {
        const metaEl = document.createElement("div");
        metaEl.className = "message-meta";
        metaEl.textContent = meta;
        msg.appendChild(metaEl);
    }

    if (techniques && techniques.length > 0) {
        const techEl = document.createElement("div");
        techEl.className = "techniques-list";
        techEl.textContent = `Techniques: ${techniques.join(", ")}`;
        msg.appendChild(techEl);
    }

    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msg;
}

function addLoadingMessage(provider) {
    const msg = document.createElement("div");
    msg.className = "message assistant";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = provider || "Assistant";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = 'Thinking<span class="loading-dots"></span>';

    msg.appendChild(label);
    msg.appendChild(bubble);
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msg;
}

function addSystemNote(text) {
    const note = document.createElement("div");
    note.className = "message assistant";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.style.fontSize = "0.8rem";
    bubble.style.color = "var(--enhance)";
    bubble.style.borderColor = "rgba(245, 158, 11, 0.3)";
    bubble.textContent = text;
    note.appendChild(bubble);
    chatContainer.appendChild(note);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setProcessing(state) {
    isProcessing = state;
    sendBtn.disabled = state;
    enhanceBtn.disabled = state;
}

// --- Utilities ---

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function timeAgo(dateStr) {
    const now = new Date();
    const date = new Date(dateStr);
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}
