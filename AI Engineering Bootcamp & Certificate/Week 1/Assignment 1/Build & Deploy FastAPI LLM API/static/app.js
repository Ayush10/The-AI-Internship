const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const enhanceBtn = document.getElementById("enhance-btn");
const providerSelect = document.getElementById("provider");
const modeSelect = document.getElementById("mode");
const promptVersionSelect = document.getElementById("prompt-version");

let isProcessing = false;

// --- Event Listeners ---

sendBtn.addEventListener("click", handleSend);
enhanceBtn.addEventListener("click", handleEnhance);

userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});

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

    const loadingEl = addLoadingMessage(provider);

    try {
        let result;

        if (mode === "summarize" && promptVersion > 0) {
            result = await callAPI("/summarize", {
                method: "POST",
                body: { text, max_length: 100 },
                params: { provider, prompt_version: promptVersion },
            });
            addMessage("assistant", result.summary, {
                provider: result.provider,
                meta: `Prompt v${result.prompt_version}`,
            });
        } else if (mode === "sentiment" && promptVersion > 0) {
            result = await callAPI("/analyze-sentiment", {
                method: "POST",
                body: { text },
                params: { provider, prompt_version: promptVersion },
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
        const result = await callAPI("/enhance-prompt", {
            method: "POST",
            body: { prompt: text },
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
