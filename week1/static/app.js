const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const enhanceBtn = document.getElementById("enhance-btn");
const sidebar = document.getElementById("sidebar");
const sidebarToggleDesktop = document.getElementById("sidebar-toggle-desktop");
const sidebarToggleMobile = document.getElementById("sidebar-toggle-mobile");
const newChatBtn = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");
const sidebarEmpty = document.getElementById("sidebar-empty");
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");

// Gate elements
const gateOverlay = document.getElementById("gate-overlay");
const gateForm = document.getElementById("gate-form");
const gateName = document.getElementById("gate-name");
const gateEmail = document.getElementById("gate-email");
const gateError = document.getElementById("gate-error");
const gateSubmit = document.getElementById("gate-submit");
const messageCounter = document.getElementById("message-counter");
const counterText = document.getElementById("counter-text");

// State
let state = {
    provider: "gemini",
    mode: "general",
    prompt_version: 0,
    isProcessing: false,
    currentConversationId: null,
    conversations: [],
    theme: localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
};

let currentUser = null;
let providerAvailability = { gemini: true, openai: true, anthropic: true };

// --- Fingerprint ---
function getFingerprint() {
    let fp = localStorage.getItem("browser_fingerprint");
    if (!fp) {
        fp = crypto.randomUUID();
        localStorage.setItem("browser_fingerprint", fp);
    }
    return fp;
}

// --- Init Theme ---
applyTheme(state.theme);

function applyTheme(theme) {
    if (theme === "dark") {
        document.documentElement.classList.add("dark");
        themeIcon.textContent = "light_mode";
    } else {
        document.documentElement.classList.remove("dark");
        themeIcon.textContent = "dark_mode";
    }
}

// --- Event Listeners ---

themeToggle?.addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", state.theme);
    applyTheme(state.theme);
});

// Button Group Toggles
document.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-group]");
    if (btn) {
        const group = btn.dataset.group;
        const value = btn.dataset.value;

        if (group === "provider" && !providerAvailability[value]) {
            addSystemNote(`${value.charAt(0).toUpperCase() + value.slice(1)} API key is not configured.`);
            return;
        }

        if (group === "prompt-version") {
            state.prompt_version = parseInt(value);
        } else {
            state[group] = value;
        }

        document.querySelectorAll(`button[data-group='${group}']`).forEach(b => {
            updateButtonVisuals(b, group, b.dataset.value === value);
        });
    }
});

function updateButtonVisuals(btn, group, isActive) {
    if (group === "provider") {
        if (isActive) {
            btn.className = "provider-btn active flex-shrink-0 px-3 py-1.5 rounded-full bg-primary border border-primary/30 flex items-center gap-2 transition-all hover:brightness-110 active:scale-95 shadow-md shadow-primary/15";
            btn.querySelector("span:last-child").className = "text-[11px] font-semibold text-white";
        } else {
            btn.className = "provider-btn flex-shrink-0 px-3 py-1.5 rounded-full bg-primary-soft dark:bg-white/[0.06] border border-primary/15 dark:border-white/[0.08] flex items-center gap-2 transition-all hover:bg-primary/15 dark:hover:bg-white/[0.1] active:scale-95";
            btn.querySelector("span:last-child").className = "text-[11px] font-semibold text-muted-light dark:text-muted-dark";
        }
    } else {
        if (isActive) {
            btn.className = "bg-white dark:bg-primary/25 text-primary dark:text-primary-light text-[10px] font-bold py-1.5 rounded-md transition-all shadow-sm dark:shadow-none";
        } else {
            btn.className = "text-muted-light dark:text-muted-dark hover:text-primary dark:hover:text-primary-light text-[10px] font-medium py-1.5 rounded-md transition-all";
        }
    }
}

sendBtn.addEventListener("click", handleSend);
enhanceBtn.addEventListener("click", handleEnhance);
newChatBtn.addEventListener("click", startNewChat);

sidebarToggleDesktop?.addEventListener("click", toggleSidebar);
sidebarToggleMobile?.addEventListener("click", toggleSidebar);

function toggleSidebar() {
    sidebar.classList.toggle("-ml-72");
    sidebar.classList.toggle("hidden");
    sidebar.classList.toggle("md:flex");
}

userInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
});

userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});

// --- Gate Logic ---

gateForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = gateName.value.trim();
    const email = gateEmail.value.trim();
    const fingerprint = getFingerprint();

    if (!name || !email) return;

    gateSubmit.disabled = true;
    gateSubmit.textContent = "Entering...";
    gateError.classList.add("hidden");

    try {
        currentUser = await callAPI("/auth/register", {
            method: "POST",
            body: { name, email, fingerprint },
        });
        localStorage.setItem("user_name", currentUser.name);
        localStorage.setItem("user_email", currentUser.email);
        showPlayground();
        updateMessageCounter();
    } catch (err) {
        gateError.textContent = err.message || "Registration failed. Try again.";
        gateError.classList.remove("hidden");
        gateSubmit.disabled = false;
        gateSubmit.textContent = "Enter Playground";
    }
});

function showGate() {
    gateOverlay.style.display = "flex";
    gateOverlay.style.opacity = "1";
    gateOverlay.classList.remove("hidden");
}

function showPlayground() {
    gateOverlay.style.opacity = "0";
    setTimeout(() => {
        gateOverlay.style.display = "none";
        gateOverlay.classList.add("hidden");
    }, 500);
}

function updateMessageCounter() {
    if (!currentUser) return;

    if (currentUser.is_admin) {
        messageCounter.classList.add("hidden");
        messageCounter.style.display = "none";
        updateUserDisplay(currentUser.name, "Unlimited");
    } else {
        const remaining = currentUser.messages_remaining;
        messageCounter.classList.remove("hidden");
        messageCounter.style.display = "flex";
        counterText.textContent = `${remaining} left`;
        counterText.classList.remove("!text-red-500");
        if (remaining <= 2) {
            counterText.classList.add("!text-red-500");
        }
        updateUserDisplay(currentUser.name, `${remaining} messages left`);
    }
}

function updateUserDisplay(name, plan) {
    const initials = name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
    const sidebarEl = document.getElementById("sidebar");
    if (!sidebarEl) return;
    const userCircle = sidebarEl.querySelector(".rounded-full.bg-gradient-to-tr");
    const userName = sidebarEl.querySelector(".truncate");
    const userPlan = sidebarEl.querySelector(".text-primary.font-medium.text-\\[10px\\]");
    if (userCircle) userCircle.textContent = initials;
    if (userName) userName.textContent = name;
    if (userPlan) userPlan.textContent = plan;
}

// --- Init ---
initApp();

async function initApp() {
    const fingerprint = getFingerprint();

    try {
        currentUser = await callAPI("/auth/me", { params: { fingerprint } });
        showPlayground();
        updateMessageCounter();
    } catch {
        showGate();
    }

    loadProviderStatus();
    loadConversations();
}

async function loadProviderStatus() {
    try {
        providerAvailability = await callAPI("/providers/status");
        document.querySelectorAll("button[data-group='provider']").forEach(btn => {
            const provider = btn.dataset.value;
            const dot = btn.querySelector("div");
            if (!providerAvailability[provider]) {
                dot.className = "w-1.5 h-1.5 rounded-full dot-unavailable";
            }
        });
    } catch (err) {
        console.warn("Failed to load provider status:", err);
    }
}

// --- Handlers ---

async function handleSend() {
    const text = userInput.value.trim();
    if (!text || state.isProcessing) return;

    if (currentUser && !currentUser.is_admin && currentUser.messages_remaining <= 0) {
        clearWelcome();
        addSystemNote("Message limit reached. Contact admin for unlimited access.");
        return;
    }

    userInput.style.height = "auto";

    const { mode, provider, prompt_version } = state;

    clearWelcome();
    addMessage("user", text);
    userInput.value = "";
    setProcessing(true);

    let endpoint = "chat";
    if (mode === "summarize" && prompt_version > 0) endpoint = "summarize";
    else if (mode === "sentiment" && prompt_version > 0) endpoint = "sentiment";

    if (!state.currentConversationId) {
        try {
            const convo = await callAPI("/api/conversations", {
                method: "POST",
                body: {
                    title: text.substring(0, 50),
                    endpoint,
                    mode,
                    provider,
                    prompt_version: prompt_version > 0 ? prompt_version : null,
                },
            });
            state.currentConversationId = convo.id;
            await loadConversations();
        } catch (err) {
            console.warn("Failed to create conversation:", err);
        }
    }

    const { loadingEl } = addLoadingMessage(provider);
    const convParam = state.currentConversationId ? { conversation_id: state.currentConversationId } : {};

    try {
        let result;

        if (endpoint === "summarize") {
            result = await callAPI("/summarize", {
                method: "POST",
                body: { text, max_length: 100 },
                params: { provider, prompt_version, ...convParam },
            });
            loadingEl.remove();
            addMessage("assistant", result.summary, {
                provider: result.provider,
                meta: `Prompt v${result.prompt_version}`,
            });
        } else if (endpoint === "sentiment") {
            result = await callAPI("/analyze-sentiment", {
                method: "POST",
                body: { text },
                params: { provider, prompt_version, ...convParam },
            });
            const formatted =
                `**Sentiment:** ${result.sentiment}\n` +
                `**Confidence:** ${(result.confidence * 100).toFixed(1)}%\n` +
                `**Explanation:** ${result.explanation}`;
            loadingEl.remove();
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
            loadingEl.remove();
            addMessage("assistant", result.response, { provider: result.provider });
        }

        // Decrement counter after successful send
        if (currentUser && !currentUser.is_admin) {
            currentUser.message_count += 1;
            currentUser.messages_remaining = Math.max(0, currentUser.messages_remaining - 1);
            updateMessageCounter();
        }
    } catch (err) {
        loadingEl.remove();
        if (err.message.includes("Message limit reached")) {
            addSystemNote("You've used all your free messages. Contact admin for unlimited access.");
            if (currentUser) {
                currentUser.messages_remaining = 0;
                updateMessageCounter();
            }
        } else {
            addMessage("assistant", `Error: ${err.message}`, { isError: true });
        }
    } finally {
        setProcessing(false);
    }
}

async function handleEnhance() {
    const text = userInput.value.trim();
    if (!text || state.isProcessing) return;

    if (currentUser && !currentUser.is_admin && currentUser.messages_remaining <= 0) {
        addSystemNote("Message limit reached. Contact admin for unlimited access.");
        return;
    }

    setProcessing(true);
    const originalBtnContent = enhanceBtn.innerHTML;
    enhanceBtn.innerHTML = '<span class="material-icons-round text-xs animate-spin">refresh</span> Enhancing...';

    try {
        const params = state.currentConversationId ? { conversation_id: state.currentConversationId } : {};
        const result = await callAPI("/enhance-prompt", {
            method: "POST",
            body: { prompt: text },
            params,
        });

        userInput.value = result.enhanced_prompt;
        userInput.focus();
        userInput.dispatchEvent(new Event("input"));

        if (result.techniques_applied.length > 0) {
            clearWelcome();
            addSystemNote(`Prompt enhanced using: ${result.techniques_applied.join(", ")}`);
        }

        if (currentUser && !currentUser.is_admin) {
            currentUser.message_count += 1;
            currentUser.messages_remaining = Math.max(0, currentUser.messages_remaining - 1);
            updateMessageCounter();
        }
    } catch (err) {
        if (err.message.includes("Message limit reached")) {
            addSystemNote("You've used all your free messages. Contact admin for unlimited access.");
            if (currentUser) {
                currentUser.messages_remaining = 0;
                updateMessageCounter();
            }
        } else {
            addSystemNote(`Enhancement failed: ${err.message}`);
        }
    } finally {
        enhanceBtn.innerHTML = originalBtnContent;
        setProcessing(false);
    }
}

// --- Conversation Management ---

function startNewChat() {
    state.currentConversationId = null;
    chatContainer.innerHTML = `
        <div class="welcome-message text-center py-12 px-4">
            <div class="w-16 h-16 bg-primary-soft dark:bg-primary/15 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-primary/10 dark:shadow-primary/20">
                <span class="material-icons-round text-3xl text-primary">auto_awesome</span>
            </div>
            <h2 class="text-xl font-bold text-text-light dark:text-text-dark mb-2">Welcome to LLM Playground</h2>
            <p class="text-muted-light dark:text-muted-dark text-sm max-w-md mx-auto leading-relaxed">
                Choose a model and mode above to get started.
                <br>Explore <strong class="text-text-light dark:text-text-dark">Summarization</strong>,
                <strong class="text-text-light dark:text-text-dark">Sentiment Analysis</strong>, or just
                <strong class="text-text-light dark:text-text-dark">Chat</strong>.
            </p>
        </div>`;
    highlightActive();
    userInput.focus();
}

async function loadConversations() {
    try {
        state.conversations = await callAPI("/api/conversations");
        renderSidebar();
    } catch (err) {
        console.warn("Failed to load conversations:", err);
    }
}

async function loadConversation(id) {
    try {
        const convo = await callAPI(`/api/conversations/${id}`);
        state.currentConversationId = convo.id;
        state.provider = convo.provider || "gemini";
        state.mode = convo.mode || "general";
        state.prompt_version = convo.prompt_version || 0;

        syncStateToUI();

        chatContainer.innerHTML = "";
        for (const msg of convo.messages) {
            if (msg.role === "user") {
                addMessage("user", msg.content);
            } else if (msg.role === "assistant") {
                addMessage("assistant", msg.content, { provider: convo.provider, meta: msg.meta });
            }
        }

        if (convo.messages.length === 0) startNewChat();
        highlightActive();

        if (window.innerWidth < 768) sidebar.classList.add("hidden");
    } catch (err) {
        addSystemNote(`Failed to load conversation: ${err.message}`);
    }
}

function syncStateToUI() {
    document.querySelectorAll("button[data-group='provider']").forEach(btn => {
        updateButtonVisuals(btn, "provider", btn.dataset.value === state.provider);
    });
    document.querySelectorAll("button[data-group='mode']").forEach(btn => {
        updateButtonVisuals(btn, "mode", btn.dataset.value === state.mode);
    });
    document.querySelectorAll("button[data-group='prompt-version']").forEach(btn => {
        updateButtonVisuals(btn, "prompt-version", parseInt(btn.dataset.value) === state.prompt_version);
    });
}

function renderSidebar() {
    conversationList.querySelectorAll(".conversation-item").forEach(el => el.remove());

    if (state.conversations.length === 0) {
        sidebarEmpty.style.display = "block";
        return;
    }
    sidebarEmpty.style.display = "none";

    for (const convo of state.conversations) {
        const div = document.createElement("div");
        const isActive = convo.id === state.currentConversationId;
        div.className = `conversation-item p-3 rounded-lg group cursor-pointer transition-colors mb-1 ${isActive ? "bg-primary-soft dark:bg-primary/10 border border-primary/20" : "hover:bg-primary-soft/50 dark:hover:bg-white/5 border border-transparent"}`;
        div.onclick = () => loadConversation(convo.id);

        const badgeColor = convo.endpoint === "chat" ? "text-primary"
            : convo.endpoint === "summarize" ? "text-emerald-500 dark:text-green-400"
            : convo.endpoint === "sentiment" ? "text-amber-500 dark:text-orange-400"
            : "text-muted-light dark:text-muted-dark";

        div.innerHTML = `
            <div class="flex items-center justify-between">
                <p class="text-xs font-medium truncate flex-1 ${isActive ? "text-primary dark:text-white" : "text-muted-light dark:text-muted-dark group-hover:text-text-light dark:group-hover:text-text-dark"}">${escapeHtml(convo.title)}</p>
                <button class="delete-btn opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 dark:hover:text-red-400 transition-opacity text-muted-light dark:text-muted-dark" title="Delete">
                    <span class="material-icons-round text-xs">close</span>
                </button>
            </div>
            <div class="flex items-center gap-2 mt-1">
                <span class="text-[10px] font-bold uppercase tracking-wider ${badgeColor}">${convo.endpoint}</span>
                <span class="text-[10px] text-muted-light dark:text-muted-dark">${timeAgo(convo.updated_at)}</span>
            </div>
        `;

        div.querySelector(".delete-btn").onclick = (e) => deleteConversation(convo.id, e);
        conversationList.appendChild(div);
    }
}

async function deleteConversation(id, e) {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;

    try {
        await callAPI(`/api/conversations/${id}`, { method: "DELETE" });
        if (state.currentConversationId === id) startNewChat();
        await loadConversations();
    } catch (err) {
        console.warn("Failed to delete conversation:", err);
    }
}

function highlightActive() {
    renderSidebar();
}

// --- UI Helpers ---

function clearWelcome() {
    const welcome = chatContainer.querySelector(".welcome-message");
    if (welcome) welcome.remove();
}

function addMessage(role, text, options = {}) {
    const { provider, meta, isError } = options;
    const msg = document.createElement("div");
    msg.className = "animate-fade-in";

    if (role === "user") {
        msg.innerHTML = `
            <div class="flex justify-end ml-12 mb-6">
                <div class="user-bubble text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-lg shadow-primary/20 max-w-full break-words">
                    <p class="text-sm leading-relaxed whitespace-pre-wrap">${escapeHtml(text)}</p>
                </div>
            </div>`;
    } else {
        let metaHtml = "";
        if (meta) {
            metaHtml = `
            <div class="flex items-center gap-2 mb-2">
                <div class="bg-primary-soft dark:bg-primary/20 text-primary px-2 py-0.5 rounded text-[9px] font-bold tracking-wider flex items-center gap-1 uppercase">
                    <span class="material-icons-round text-[10px]">auto_awesome</span>
                    ${typeof meta === "string" ? meta : "Analysis Result"}
                </div>
            </div>`;
        }

        msg.innerHTML = `
            <div class="mr-12 mb-6">
                <div class="assistant-bubble-light rounded-2xl rounded-tl-none p-4 relative overflow-hidden">
                    ${metaHtml}
                    <div class="text-sm text-text-light dark:text-text-dark leading-relaxed space-y-2 whitespace-pre-wrap">${formatContent(text)}</div>
                    <div class="flex items-center gap-4 border-t border-border-light dark:border-border-dark pt-3 mt-4">
                        <div class="flex items-center gap-1 text-[10px] text-muted-light dark:text-muted-dark" title="Provider">
                            <span class="material-icons-round text-xs">vpn_key</span>
                            ${provider || "AI"}
                        </div>
                        <div class="ml-auto flex gap-2">
                            <span class="material-icons-round text-muted-light dark:text-muted-dark text-xs hover:text-primary cursor-pointer transition-colors copy-btn" title="Copy">content_copy</span>
                            <span class="material-icons-round text-muted-light dark:text-muted-dark text-xs hover:text-primary cursor-pointer transition-colors" title="Like">thumb_up</span>
                        </div>
                    </div>
                </div>
            </div>`;

        if (isError) {
            msg.querySelector(".assistant-bubble-light").style.borderColor = "rgba(239, 68, 68, 0.3)";
            msg.querySelector(".text-text-light").classList.add("!text-red-500", "dark:!text-red-400");
        }

        // Copy button handler
        const copyBtn = msg.querySelector(".copy-btn");
        if (copyBtn) {
            copyBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(text).then(() => {
                    copyBtn.textContent = "check";
                    setTimeout(() => { copyBtn.textContent = "content_copy"; }, 1500);
                });
            });
        }
    }

    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msg;
}

function addLoadingMessage(provider) {
    const msg = document.createElement("div");
    msg.className = "mr-12 mb-6 animate-fade-in";
    msg.innerHTML = `
        <div class="assistant-bubble-light rounded-2xl rounded-tl-none p-4 flex items-center gap-3 w-fit">
            <div class="flex gap-1.5">
                <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 rounded-full bg-primary-light animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 rounded-full bg-primary/50 animate-bounce" style="animation-delay: 300ms"></div>
            </div>
            <span class="text-xs text-muted-light dark:text-muted-dark">${provider || "Thinking"}...</span>
        </div>`;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return { loadingEl: msg };
}

function addSystemNote(text) {
    const msg = document.createElement("div");
    msg.className = "flex justify-center mb-4 opacity-80";
    msg.innerHTML = `
        <div class="bg-primary-soft dark:bg-primary/10 border border-primary/15 dark:border-primary/20 px-3 py-1 rounded-full flex items-center gap-2">
            <span class="material-icons-round text-primary text-xs">info</span>
            <span class="text-xs text-primary font-medium">${text}</span>
        </div>`;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setProcessing(isProc) {
    state.isProcessing = isProc;
    sendBtn.disabled = isProc;
    sendBtn.classList.toggle("opacity-50", isProc);
    sendBtn.classList.toggle("cursor-not-allowed", isProc);
    enhanceBtn.disabled = isProc;
    enhanceBtn.classList.toggle("opacity-50", isProc);
}

function formatContent(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-text-light dark:text-text-dark font-semibold">$1</strong>')
        .replace(/```([\s\S]*?)```/g, '<div class="bg-gray-100 dark:bg-black/30 text-text-light dark:text-text-dark p-3 rounded-lg my-2 font-mono text-xs overflow-x-auto border border-border-light dark:border-border-dark">$1</div>');
}

// --- Utilities ---

function escapeHtml(str) {
    if (!str) return "";
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
    return date.toLocaleDateString();
}

async function callAPI(path, { method = "GET", body = null, params = {} } = {}) {
    const base = window.__BASE_PATH__ || "";
    const url = new URL(base + path, window.location.origin);

    // Auto-attach fingerprint to LLM and conversation endpoints
    if (!path.startsWith("/auth/") && !path.startsWith("/health") && !path.startsWith("/providers/")) {
        const fp = getFingerprint();
        if (fp && !params.fingerprint) params.fingerprint = fp;
    }

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
