// ─── State ───
const state = {
    activeTab: "notebook",
    search_mode: "hybrid",
    chunk_size: 500,
    topic_filter: "",
    isProcessing: false,
    autoplayRunning: false,
    autoplayResults: null,
    theme: localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
};

// ─── Theme ───
applyTheme(state.theme);

function applyTheme(theme) {
    if (theme === "dark") {
        document.documentElement.classList.add("dark");
        document.getElementById("theme-icon").textContent = "light_mode";
    } else {
        document.documentElement.classList.remove("dark");
        document.getElementById("theme-icon").textContent = "dark_mode";
    }
}

document.getElementById("theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", state.theme);
    applyTheme(state.theme);
});

// ─── Tabs (3 tabs: notebook, chat, results) ───
function switchTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll(".tab-btn").forEach(b => {
        if (b.dataset.tab === tab) {
            b.className = "tab-btn bg-white dark:bg-primary/25 text-primary dark:text-primary-light text-[11px] font-bold py-1.5 px-3 rounded-md transition-all shadow-sm";
        } else {
            b.className = "tab-btn text-muted-light dark:text-muted-dark hover:text-primary text-[11px] font-medium py-1.5 px-3 rounded-md transition-all";
        }
    });
    document.getElementById("view-notebook").classList.toggle("hidden", tab !== "notebook");
    document.getElementById("view-chat").classList.toggle("hidden", tab !== "chat");
    document.getElementById("view-results").classList.toggle("hidden", tab !== "results");
}

document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ─── Chat Settings Toggles ───
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".setting-btn");
    if (!btn) return;
    const group = btn.dataset.group;
    const value = btn.dataset.value;
    state[group] = group === "chunk_size" ? parseInt(value) : value;

    btn.parentElement.querySelectorAll(".setting-btn").forEach(b => {
        if (b.dataset.value === value) {
            b.className = "setting-btn active text-[10px] font-bold py-1 px-2.5 rounded-md bg-white dark:bg-primary/25 text-primary dark:text-primary-light shadow-sm";
        } else {
            b.className = "setting-btn text-[10px] font-medium py-1 px-2.5 rounded-md text-muted-light dark:text-muted-dark";
        }
    });
});

document.getElementById("topic-filter").addEventListener("change", (e) => {
    state.topic_filter = e.target.value;
});

// ─── API Helper ───
async function callAPI(path, { method = "GET", body = null } = {}) {
    const base = window.__BASE_PATH__ || "";
    const url = new URL(base + path, window.location.origin);
    const options = { method, headers: {} };
    if (body) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ─── Markdown Renderer ───
function renderMarkdown(md) {
    if (typeof marked !== "undefined") {
        return marked.parse(md);
    }
    return md
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/^---$/gm, '<hr>')
        .replace(/\n/g, '<br>');
}

// ─── Escape HTML ───
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ═══════════════════════════════════════════
// NOTEBOOK
// ═══════════════════════════════════════════

const notebookContainer = document.getElementById("notebook-cells");

async function loadNotebook() {
    try {
        const cells = await callAPI("/api/rag/notebook");
        notebookContainer.innerHTML = "";
        cells.forEach(cell => renderNotebookCell(cell));
    } catch (err) {
        notebookContainer.innerHTML = `<p class="text-red-500 text-sm">Failed to load notebook: ${err.message}</p>`;
    }
}

function renderNotebookCell(cell) {
    const el = document.createElement("div");
    el.className = "nb-cell animate-fade-in";
    el.id = `cell-${cell.cell_id}`;

    if (cell.cell_type === "markdown") {
        el.innerHTML = `<div class="md-content p-4 text-sm">${renderMarkdown(cell.content)}</div>`;
    } else {
        const stepBadge = cell.step ? `<span class="step-badge">Step ${cell.step}</span>` : "";
        const runBtn = cell.is_runnable
            ? `<button class="nb-run-btn" data-cell="${cell.cell_id}" onclick="runCell('${cell.cell_id}')"><span class="material-icons-round">play_arrow</span> Run</button>`
            : "";

        el.innerHTML = `
            <div class="nb-cell-header">
                ${stepBadge}
                <span class="text-muted-light dark:text-muted-dark flex-1">${cell.cell_id}</span>
                ${runBtn}
            </div>
            <textarea class="nb-code-editor" id="editor-${cell.cell_id}" spellcheck="false">${escapeHtml(cell.content)}</textarea>
            <div class="nb-output ${cell.default_output ? '' : 'hidden'}" id="output-${cell.cell_id}">${cell.default_output ? escapeHtml(cell.default_output) : ''}</div>
        `;
    }

    notebookContainer.appendChild(el);

    const textarea = el.querySelector("textarea");
    if (textarea) {
        autoResize(textarea);
        textarea.addEventListener("input", () => autoResize(textarea));
        textarea.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = textarea.selectionStart;
                textarea.value = textarea.value.substring(0, start) + "    " + textarea.value.substring(textarea.selectionEnd);
                textarea.selectionStart = textarea.selectionEnd = start + 4;
            }
        });
    }
}

function autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
}

async function runCell(cellId) {
    const btn = document.querySelector(`.nb-run-btn[data-cell="${cellId}"]`);
    const outputEl = document.getElementById(`output-${cellId}`);
    const editorEl = document.getElementById(`editor-${cellId}`);

    if (!btn || !outputEl) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons-round animate-spin">refresh</span> Running...';
    outputEl.classList.remove("hidden", "has-error");
    outputEl.textContent = "Executing...";

    try {
        const result = await callAPI("/api/rag/notebook/run", {
            method: "POST",
            body: { cell_id: cellId, code: editorEl ? editorEl.value : null },
        });

        if (result.error) {
            outputEl.classList.add("has-error");
            outputEl.textContent = result.output + "\n\nERROR: " + result.error;
        } else {
            outputEl.textContent = result.output;
        }
        outputEl.textContent += `\n\n⏱ ${result.execution_time}s`;
    } catch (err) {
        outputEl.classList.add("has-error");
        outputEl.textContent = "Error: " + err.message;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons-round">play_arrow</span> Run';
    }
}

// Run All
document.getElementById("run-all-btn").addEventListener("click", async () => {
    const btn = document.getElementById("run-all-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons-round animate-spin">refresh</span> Running All...';

    const runnableCells = ["step1_load", "step2_chunk", "step3_embed", "step4_retrieve", "step5_query", "step6_eval"];
    for (const cellId of runnableCells) {
        const cellEl = document.getElementById(`cell-${cellId}`);
        if (cellEl) cellEl.scrollIntoView({ behavior: "smooth", block: "center" });
        await runCell(cellId);
    }

    btn.disabled = false;
    btn.innerHTML = '<span class="material-icons-round">play_arrow</span> Run All';
});

// ═══════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════

const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", handleSend);
userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});
userInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
});

// Example query chips
document.querySelectorAll(".example-q").forEach(btn => {
    btn.addEventListener("click", () => {
        userInput.value = btn.dataset.q;
        userInput.dispatchEvent(new Event("input"));
        handleSend();
    });
});

async function handleSend() {
    const text = userInput.value.trim();
    if (!text || state.isProcessing) return;

    clearWelcome();
    addMessage("user", text);
    userInput.value = "";
    userInput.style.height = "auto";
    state.isProcessing = true;
    sendBtn.disabled = true;

    const loadingEl = addLoading();

    try {
        const result = await callAPI("/api/rag/query", {
            method: "POST",
            body: {
                question: text,
                search_mode: state.search_mode,
                chunk_size: state.chunk_size,
                num_results: 3,
                topic_filter: state.topic_filter || null,
            },
        });

        loadingEl.remove();
        addMessage("assistant", result.answer, result.sources);
    } catch (err) {
        loadingEl.remove();
        addMessage("assistant", `Error: ${err.message}`, null, true);
    } finally {
        state.isProcessing = false;
        sendBtn.disabled = false;
    }
}

function clearWelcome() {
    const w = chatContainer.querySelector(".welcome-message");
    if (w) w.remove();
}

function addMessage(role, text, sources = null, isError = false) {
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
        const formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');

        let sourcesHtml = "";
        if (sources && sources.length > 0) {
            const chips = sources.map(s =>
                `<span class="source-chip"><span class="material-icons-round text-xs">description</span>${s.source} <span class="text-[9px] text-muted-light dark:text-muted-dark">${s.topic || ""} ${s.year || ""}</span></span>`
            ).join("");

            const details = sources.map(s =>
                `<div class="mt-2 p-3 rounded-lg bg-black/[0.02] dark:bg-white/[0.02] border border-border-light dark:border-border-dark">
                    <p class="text-[10px] font-bold text-primary mb-1">${s.source} — ${s.topic || "N/A"}, ${s.year || "N/A"}</p>
                    <p class="text-[11px] text-muted-light dark:text-muted-dark leading-relaxed">${escapeHtml(s.content.substring(0, 300))}...</p>
                </div>`
            ).join("");

            sourcesHtml = `
                <div class="mt-3 pt-3 border-t border-border-light dark:border-border-dark">
                    <div class="flex flex-wrap gap-1.5 mb-2">${chips}</div>
                    <details class="text-xs">
                        <summary class="text-muted-light dark:text-muted-dark cursor-pointer hover:text-primary transition-colors font-medium">Show retrieved chunks</summary>
                        ${details}
                    </details>
                </div>`;
        }

        msg.innerHTML = `
            <div class="mr-12 mb-6">
                <div class="assistant-bubble rounded-2xl rounded-tl-none p-4 ${isError ? 'border-red-500/30' : ''}">
                    <div class="text-sm leading-relaxed space-y-1 ${isError ? 'text-red-500 dark:text-red-400' : 'text-text-light dark:text-text-dark'}">${formattedText}</div>
                    ${sourcesHtml}
                    <div class="flex items-center gap-4 pt-3 mt-3 border-t border-border-light dark:border-border-dark">
                        <div class="flex items-center gap-1 text-[10px] text-muted-light dark:text-muted-dark">
                            <span class="material-icons-round text-xs">smart_toy</span>
                            GLM-5 · ${state.search_mode} · chunk ${state.chunk_size}
                        </div>
                        <span class="material-icons-round text-muted-light dark:text-muted-dark text-xs hover:text-primary cursor-pointer transition-colors ml-auto copy-btn" title="Copy">content_copy</span>
                    </div>
                </div>
            </div>`;

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
}

function addLoading() {
    const msg = document.createElement("div");
    msg.className = "mr-12 mb-6 animate-fade-in";
    msg.innerHTML = `
        <div class="assistant-bubble rounded-2xl rounded-tl-none p-4 flex items-center gap-3 w-fit">
            <div class="flex gap-1.5">
                <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay:0ms"></div>
                <div class="w-2 h-2 rounded-full bg-primary-light animate-bounce" style="animation-delay:150ms"></div>
                <div class="w-2 h-2 rounded-full bg-primary/50 animate-bounce" style="animation-delay:300ms"></div>
            </div>
            <span class="text-xs text-muted-light dark:text-muted-dark">Searching papers & generating answer...</span>
        </div>`;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msg;
}

// ═══════════════════════════════════════════
// AUTOPLAY
// ═══════════════════════════════════════════

const autoplayBtn = document.getElementById("autoplay-btn");
autoplayBtn.addEventListener("click", startAutoplay);

function updateAutoplayBtn(status) {
    const icon = autoplayBtn.querySelector(".material-icons-round");
    const label = autoplayBtn.querySelector(".autoplay-label");
    autoplayBtn.classList.remove("running");

    if (status === "running") {
        icon.textContent = "refresh";
        icon.classList.add("animate-spin");
        label.textContent = "Running...";
        autoplayBtn.disabled = true;
        autoplayBtn.classList.add("running");
    } else if (status === "done") {
        icon.textContent = "check_circle";
        icon.classList.remove("animate-spin");
        label.textContent = "Done!";
        autoplayBtn.disabled = false;
        setTimeout(() => {
            icon.textContent = "rocket_launch";
            label.textContent = "Autoplay";
        }, 3000);
    } else if (status === "error") {
        icon.textContent = "error";
        icon.classList.remove("animate-spin");
        label.textContent = "Error";
        autoplayBtn.disabled = false;
        setTimeout(() => {
            icon.textContent = "rocket_launch";
            label.textContent = "Autoplay";
        }, 3000);
    } else {
        icon.textContent = "rocket_launch";
        icon.classList.remove("animate-spin");
        label.textContent = "Autoplay";
        autoplayBtn.disabled = false;
    }
}

function startAutoplay() {
    if (state.autoplayRunning) return;
    state.autoplayRunning = true;

    switchTab("results");

    // Show progress, hide content and empty state
    document.getElementById("autoplay-progress").classList.remove("hidden");
    document.getElementById("results-content").classList.add("hidden");
    document.getElementById("results-empty").classList.add("hidden");

    // Reset progress UI
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("progress-log").innerHTML = "";
    document.querySelectorAll(".phase-dot").forEach(d => {
        d.className = "phase-dot pending";
    });

    updateAutoplayBtn("running");

    const base = window.__BASE_PATH__ || "";
    const eventSource = new EventSource(`${base}/api/rag/autoplay?theme=${state.theme}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.heartbeat) {
            // Update the last log line with elapsed time instead of adding new lines
            const log = document.getElementById("progress-log");
            const lastLine = log.lastElementChild;
            if (lastLine && lastLine.dataset.heartbeat) {
                lastLine.textContent = `    ⏳ ${data.message}`;
            } else {
                const line = document.createElement("div");
                line.dataset.heartbeat = "true";
                line.className = "text-muted-light dark:text-muted-dark italic";
                line.textContent = `    ⏳ ${data.message}`;
                log.appendChild(line);
                log.scrollTop = log.scrollHeight;
            }
            return;
        }

        handleAutoplayEvent(data);

        if (data.phase === "complete") {
            eventSource.close();
            state.autoplayRunning = false;
            updateAutoplayBtn("done");
            loadResults();
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        state.autoplayRunning = false;
        updateAutoplayBtn("error");
        addProgressLog("Connection error. Check if the server is running.", true);
    };
}

function handleAutoplayEvent(data) {
    // Update progress bar
    if (data.overall && data.overall_total) {
        const pct = Math.round((data.overall / data.overall_total) * 100);
        document.getElementById("progress-fill").style.width = pct + "%";
    }

    // Update phase dots
    const phases = ["notebook", "chat", "eval", "charts"];
    const currentIdx = phases.indexOf(data.phase);
    document.querySelectorAll(".phase-dot").forEach((dot, i) => {
        if (i < currentIdx) {
            dot.className = "phase-dot done";
        } else if (i === currentIdx) {
            dot.className = data.status === "done" && data.phase !== phases[currentIdx]
                ? "phase-dot done" : "phase-dot active";
        } else {
            dot.className = "phase-dot pending";
        }
    });

    // Log message
    if (data.message) {
        const isError = data.error || data.status === "error";
        addProgressLog(data.message + (data.time ? ` (${data.time.toFixed(1)}s)` : ""), isError);
    } else if (data.status === "done" && data.cell_id) {
        addProgressLog(`Done: ${data.cell_id} (${data.time ? data.time.toFixed(1) + "s" : ""})`);
    } else if (data.status === "done" && data.config) {
        const sh = data.scores_heuristic || {};
        addProgressLog(`Done: ${data.config} — R:${sh.retrieval || "?"}/5 F:${sh.faithfulness || "?"}/5 C:${sh.correctness || "?"}/5`);
    } else if (data.status === "done" && data.chart_names) {
        addProgressLog(`Charts generated: ${data.chart_names.join(", ")}`);
    }

    // Update title
    const titleMap = {
        notebook: `Running Notebook (${data.step || ""}/${data.total || ""})`,
        chat: `Running Q&A (${data.step || ""}/${data.total || ""})`,
        eval: `Evaluating (${data.step || ""}/${data.total || ""})`,
        charts: "Generating Charts...",
        complete: "Autoplay Complete!",
    };
    const titleEl = document.getElementById("progress-title");
    if (titleMap[data.phase]) titleEl.textContent = titleMap[data.phase];

    // Update spinner on complete
    if (data.phase === "complete") {
        document.getElementById("progress-spinner").textContent = "check_circle";
        document.getElementById("progress-spinner").classList.remove("animate-spin");
        document.getElementById("progress-spinner").classList.add("text-green-500");
        document.querySelectorAll(".phase-dot").forEach(d => d.className = "phase-dot done");
        document.getElementById("progress-fill").style.width = "100%";
    }
}

function addProgressLog(message, isError = false) {
    const log = document.getElementById("progress-log");
    const line = document.createElement("div");
    line.className = isError ? "text-red-500" : "";
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] ${message}`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

async function loadResults() {
    try {
        const results = await callAPI("/api/rag/results");
        state.autoplayResults = results;
        renderResults(results);
    } catch (err) {
        addProgressLog("Failed to load results: " + err.message, true);
    }
}

// ═══════════════════════════════════════════
// RESULTS RENDERING
// ═══════════════════════════════════════════

function renderResults(results) {
    document.getElementById("autoplay-progress").classList.add("hidden");
    document.getElementById("results-content").classList.remove("hidden");
    document.getElementById("results-empty").classList.add("hidden");

    // Architecture diagram
    const archContainer = document.getElementById("architecture-container");
    if (results.charts && results.charts.architecture_diagram) {
        archContainer.innerHTML = results.charts.architecture_diagram;
    }

    // Charts
    const chartNames = ["evaluation_scores", "chunk_comparison", "search_comparison", "judge_comparison"];
    for (const name of chartNames) {
        const container = document.getElementById(`chart-${name}`);
        if (container && results.charts && results.charts[name]) {
            // Keep the label, add image
            const label = container.querySelector("p");
            container.innerHTML = "";
            if (label) container.appendChild(label);
            const img = document.createElement("img");
            img.src = `data:image/png;base64,${results.charts[name]}`;
            img.alt = name;
            img.className = "w-full rounded-lg";
            container.appendChild(img);
        }
    }

    // Evaluation table
    renderEvalTable(results.eval_results);

    // Chat responses
    renderChatResults(results.chat_responses);
}

function renderEvalTable(evalResults) {
    const container = document.getElementById("eval-table-container");
    if (!evalResults || !evalResults.length) {
        container.innerHTML = '<p class="p-4 text-sm text-muted-light dark:text-muted-dark">No evaluation data.</p>';
        return;
    }

    let rows = "";
    for (const r of evalResults) {
        const sh = r.scores_heuristic || {};
        const sj = r.scores_llm_judge || {};
        rows += `<tr>
            <td>${r.chunk_size}</td>
            <td>${r.search_mode}</td>
            <td>${sh.retrieval ?? "-"}/5</td>
            <td>${sh.faithfulness ?? "-"}/5</td>
            <td>${sh.correctness ?? "-"}/5</td>
            <td>${sj.retrieval ?? "-"}/5</td>
            <td>${sj.faithfulness ?? "-"}/5</td>
            <td>${typeof sj.correctness === "number" ? sj.correctness.toFixed(2) : "-"}/5</td>
        </tr>`;
    }

    container.innerHTML = `
        <table class="eval-table">
            <thead>
                <tr>
                    <th rowspan="2">Chunk</th>
                    <th rowspan="2">Search</th>
                    <th colspan="3" class="text-center">Heuristic</th>
                    <th colspan="3" class="text-center">LLM Judge</th>
                </tr>
                <tr>
                    <th>Retrieval</th><th>Faithful</th><th>Correct</th>
                    <th>Retrieval</th><th>Faithful</th><th>Correct</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function renderChatResults(chatResponses) {
    const container = document.getElementById("chat-results-container");
    if (!chatResponses || !chatResponses.length) {
        container.innerHTML = '<p class="text-sm text-muted-light dark:text-muted-dark">No chat results.</p>';
        return;
    }

    container.innerHTML = chatResponses.map((resp, i) => {
        const sourcesText = (resp.sources || []).map(s => s.source || "unknown").join(", ");
        const answerPreview = (resp.answer || "").substring(0, 400);
        return `
        <div class="chart-card p-4">
            <p class="text-xs font-bold text-primary mb-1">Q${i + 1}: ${escapeHtml(resp.question)}</p>
            <p class="text-sm text-text-light dark:text-text-dark leading-relaxed mb-2">${escapeHtml(answerPreview)}${resp.answer.length > 400 ? "..." : ""}</p>
            <p class="text-[10px] text-muted-light dark:text-muted-dark">Sources: ${escapeHtml(sourcesText)}</p>
        </div>`;
    }).join("");
}

// ═══════════════════════════════════════════
// DOWNLOADS
// ═══════════════════════════════════════════

document.addEventListener("click", (e) => {
    const btn = e.target.closest(".download-btn");
    if (!btn) return;
    const file = btn.dataset.file;
    if (!file) return;

    const base = window.__BASE_PATH__ || "";
    if (file === "zip") {
        window.location.href = base + "/api/rag/download/zip";
    } else {
        window.location.href = `${base}/api/rag/download/${file}`;
    }
});

// ─── Init ───
loadNotebook();
