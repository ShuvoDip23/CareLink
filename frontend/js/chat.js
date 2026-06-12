const API_URL = "http://127.0.0.1:5000";

let currentSessionId = null;
let currentDbSessionId = null;
let isAuthenticated = false;
let isWaitingForResponse = false;
let loadingMessageEl = null;

document.addEventListener("DOMContentLoaded", async () => {
  await checkChatAuth();

  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter" && !this.disabled && !isWaitingForResponse) {
        sendMessage();
      }
    });
  }
});

async function checkChatAuth() {
  try {
    const response = await fetch(`${API_URL}/api/me`, {
      credentials: "include",
    });
    const data = await response.json();
    isAuthenticated = data.authenticated;
    return data;
  } catch (error) {
    console.error("Auth check failed:", error);
    isAuthenticated = false;
    return { authenticated: false };
  }
}

async function openChatbot() {
  await checkChatAuth();

  const chatWidget = document.getElementById("chatWidget");
  const chatFloatBtn = document.getElementById("chatFloatBtn");

  if (chatWidget) {
    chatWidget.classList.remove("hidden");
    chatWidget.classList.add("flex");
  }

  document.body.classList.add("chat-open");

  if (chatFloatBtn) {
    chatFloatBtn.classList.add("hidden");
  }

  if (!isAuthenticated) {
    showLoginPrompt();
  } else {
    showWelcomeMenu();
  }
}

function closeChatbot() {
  const chatWidget = document.getElementById("chatWidget");
  const chatFloatBtn = document.getElementById("chatFloatBtn");

  if (chatWidget) {
    chatWidget.classList.add("hidden");
    chatWidget.classList.remove("flex");
  }

  document.body.classList.remove("chat-open");

  if (chatFloatBtn) {
    chatFloatBtn.classList.remove("hidden");
  }
}

function toggleChatbot() {
  const chatWidget = document.getElementById("chatWidget");

  if (chatWidget.classList.contains("hidden")) {
    openChatbot();
  } else {
    closeChatbot();
  }
}

function showLoginPrompt() {
  const chatMessages = document.getElementById("chatMessages");
  const inputArea = document.querySelector(".chat-input-area");
  const startBtn = document.getElementById("startBtn");
  const historyBtn = document.getElementById("historyBtn");

  if (!chatMessages) return;

  chatMessages.innerHTML = `
    <div class="h-full flex items-center justify-center">
      <div class="w-full bg-white border border-slate-200 rounded-3xl p-7 shadow-sm text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-blue-50 flex items-center justify-center">
          <svg class="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8"/>
          </svg>
        </div>
        <h3 class="text-lg font-bold text-slate-900 mb-2">Login Required</h3>
        <p class="text-sm text-slate-600 leading-relaxed mb-6">
          Please log in to use the Health Assistant, continue consultations, and save your history.
        </p>
        <div class="grid grid-cols-2 gap-3">
          <a href="login.html" class="inline-flex items-center justify-center px-4 py-3 bg-primary text-white font-semibold rounded-xl hover:bg-primary-dark transition-colors">
            Login
          </a>
          <a href="register.html" class="inline-flex items-center justify-center px-4 py-3 bg-white border border-slate-300 text-slate-700 font-semibold rounded-xl hover:border-primary hover:text-primary transition-colors">
            Sign Up
          </a>
        </div>
      </div>
    </div>
  `;

  if (inputArea) inputArea.style.display = "none";
  if (startBtn) startBtn.style.display = "none";
  if (historyBtn) historyBtn.style.display = "none";
}

function showWelcomeMenu() {
  const chatMessages = document.getElementById("chatMessages");
  const inputArea = document.querySelector(".chat-input-area");
  const startBtn = document.getElementById("startBtn");
  const historyBtn = document.getElementById("historyBtn");

  if (!chatMessages) return;

  chatMessages.innerHTML = `
    <div class="space-y-4">
      <div class="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-2xl bg-blue-50 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
            </svg>
          </div>
          <div>
            <div class="text-sm font-semibold text-slate-900 mb-1">Health Assistant</div>
            <p class="text-sm text-slate-600 leading-relaxed">
              Welcome back. Start a new consultation for symptom assessment, or review one of your previous chats.
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-3">
        <div class="bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-100 rounded-2xl p-4">
          <div class="text-xs font-semibold uppercase tracking-wide text-primary mb-1">What this assistant can do</div>
          <div class="text-sm text-slate-700 leading-relaxed">
            Understand symptoms, ask follow-up questions, detect warning signs, and suggest the right specialist.
          </div>
        </div>
      </div>
    </div>
  `;

  if (inputArea) inputArea.style.display = "flex";
  if (startBtn) startBtn.style.display = "block";
  if (historyBtn) historyBtn.style.display = "block";

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  if (chatInput) chatInput.disabled = true;
  if (sendBtn) sendBtn.disabled = true;
}

async function startConsultation() {
  await checkChatAuth();

  if (!isAuthenticated) {
    showLoginPrompt();
    return;
  }

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const startBtn = document.getElementById("startBtn");
  const chatMessages = document.getElementById("chatMessages");

  try {
    showLoadingMessage("Starting a new consultation...");

    const response = await fetch(`${API_URL}/api/session/start`, {
      method: "POST",
      credentials: "include",
    });

    removeLoadingMessage();

    if (response.status === 401) {
      showLoginPrompt();
      return;
    }

    const data = await response.json();

    currentSessionId = data.session_id;
    currentDbSessionId = data.db_session_id;

    chatMessages.innerHTML = "";
    addBotMessage(data.message);

    if (chatInput) {
      chatInput.disabled = false;
      chatInput.focus();
    }

    if (sendBtn) sendBtn.disabled = false;
    if (startBtn) startBtn.style.display = "none";
  } catch (error) {
    removeLoadingMessage();
    console.error("Failed to start consultation:", error);
    addBotMessage(
      "Sorry, I encountered an error while starting the consultation. Please try again.",
      "text",
    );
  }
}

async function sendMessage() {
  const chatInput = document.getElementById("chatInput");

  if (!chatInput || !currentDbSessionId || isWaitingForResponse) return;

  const message = chatInput.value.trim();
  if (message === "") return;

  addUserMessage(message);
  chatInput.value = "";

  setWaitingState(true);
  showLoadingMessage("Analyzing symptoms and preparing the next response...");

  try {
    const response = await fetch(`${API_URL}/api/chat/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        message: message,
        db_session_id: currentDbSessionId,
      }),
    });

    removeLoadingMessage();

    if (response.status === 401) {
      setWaitingState(false);
      showLoginPrompt();
      return;
    }

    const data = await response.json();
    addBotMessage(
      data.message,
      data.message_type,
      data.buttons,
      data.reasoning,
    );

    if (
      data.message_type === "recommendation" ||
      data.message_type === "emergency"
    ) {
      currentDbSessionId = currentDbSessionId;
    }

    setWaitingState(false);
  } catch (error) {
    removeLoadingMessage();
    setWaitingState(false);
    console.error("Failed to send message:", error);
    addBotMessage("Sorry, I encountered an error. Please try again.", "text");
  }
}

async function loadChatHistory() {
  await checkChatAuth();

  if (!isAuthenticated) {
    showLoginPrompt();
    return;
  }

  const chatMessages = document.getElementById("chatMessages");
  const startBtn = document.getElementById("startBtn");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");

  try {
    showLoadingMessage("Loading previous consultations...");

    const response = await fetch(`${API_URL}/api/chat/history`, {
      method: "GET",
      credentials: "include",
    });

    removeLoadingMessage();

    if (response.status === 401) {
      showLoginPrompt();
      return;
    }

    const data = await response.json();
    const history = data.history || [];

    if (history.length === 0) {
      chatMessages.innerHTML = `
        <div class="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
          <div class="text-sm font-semibold text-slate-900 mb-1">Previous Chats</div>
          <p class="text-sm text-slate-600">You do not have any previous chat history yet.</p>
        </div>
      `;
      if (startBtn) startBtn.style.display = "block";
      if (chatInput) chatInput.disabled = true;
      if (sendBtn) sendBtn.disabled = true;
      return;
    }

    let html = `
      <div class="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-base font-bold text-slate-900">Previous Consultations</div>
            <div class="text-xs text-slate-500 mt-1">Tap any consultation to reopen its messages</div>
          </div>
        </div>
        <div class="space-y-3">
    `;

    history.forEach((item) => {
      const session = item.session;
      const dateText = new Date(session.started_at).toLocaleString();
      const risk = session.risk_level || "unknown";
      const specialty = session.recommended_specialty || "Not assigned";

      html += `
        <button onclick="loadSessionMessages(${session.id})"
          class="w-full text-left p-4 border border-slate-200 rounded-2xl hover:border-primary hover:shadow-sm transition-all bg-slate-50/70">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-sm font-semibold text-slate-900">${dateText}</div>
              <div class="text-xs text-slate-500 mt-1">Recommended specialist: ${escapeHtml(specialty)}</div>
            </div>
            ${buildRiskBadge(risk)}
          </div>
        </button>
      `;
    });

    html += `
        </div>
      </div>
    `;

    chatMessages.innerHTML = html;

    if (startBtn) startBtn.style.display = "block";
    if (chatInput) chatInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } catch (error) {
    removeLoadingMessage();
    console.error("Failed to load history:", error);
    addBotMessage("Sorry, I could not load your chat history.", "text");
  }
}

async function loadSessionMessages(sessionId) {
  const chatMessages = document.getElementById("chatMessages");
  const startBtn = document.getElementById("startBtn");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");

  try {
    showLoadingMessage("Opening consultation...");

    const response = await fetch(`${API_URL}/api/chat/session/${sessionId}`, {
      method: "GET",
      credentials: "include",
    });

    removeLoadingMessage();

    if (response.status === 401) {
      showLoginPrompt();
      return;
    }

    const data = await response.json();
    const messages = data.messages || [];

    chatMessages.innerHTML = "";

    messages.forEach((msg) => {
      if (msg.sender === "user") {
        addUserMessage(msg.message);
      } else {
        addBotMessage(msg.message, msg.message_type || "text");
      }
    });

    currentDbSessionId = null;
    currentSessionId = null;

    if (startBtn) startBtn.style.display = "block";
    if (chatInput) chatInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } catch (error) {
    removeLoadingMessage();
    console.error("Failed to load session messages:", error);
    addBotMessage("Sorry, I could not load that previous chat.", "text");
  }
}

function addUserMessage(message) {
  const chatMessages = document.getElementById("chatMessages");

  const userMessage = document.createElement("div");
  userMessage.className = "flex justify-end";
  userMessage.innerHTML = `
    <div class="max-w-[82%] bg-primary text-white rounded-[22px] rounded-tr-md px-4 py-3.5 shadow-md shadow-blue-900/10">
      <p class="text-sm leading-relaxed">${escapeHtml(message)}</p>
    </div>
  `;
  chatMessages.appendChild(userMessage);
  scrollChatToBottom();
}

function addBotMessage(
  message,
  messageType = "text",
  buttons = null,
  reasoning = null,
) {
  const chatMessages = document.getElementById("chatMessages");
  const botMessage = document.createElement("div");
  botMessage.className = "flex justify-start";

  const parsed = parseBotMessageSections(message);

  let wrapperClass =
    "max-w-[88%] bg-white border border-slate-200 rounded-[24px] rounded-tl-md p-4 shadow-sm";
  let accentClass = "bg-blue-50 text-primary";
  let headerTitle = "Health Assistant";

  if (messageType === "emergency" || messageType === "context_warning") {
    wrapperClass =
      "max-w-[88%] bg-red-50 border border-red-200 rounded-[24px] rounded-tl-md p-4 shadow-sm";
    accentClass = "bg-red-100 text-red-700";
    headerTitle = "Emergency Alert";
  } else if (messageType === "recommendation") {
    wrapperClass =
      "max-w-[88%] bg-blue-50 border border-blue-200 rounded-[24px] rounded-tl-md p-4 shadow-sm";
    accentClass = "bg-blue-100 text-primary";
    headerTitle = "Assessment Summary";
  }

  let contentHTML = "";

  if (parsed.isStructured) {
    contentHTML += `
      <div class="flex items-start justify-between gap-3 mb-3">
        <div class="flex items-center gap-2">
          <div class="w-9 h-9 rounded-xl ${accentClass} flex items-center justify-center shrink-0">
            ${getMessageIcon(messageType)}
          </div>
          <div>
            <div class="text-sm font-bold text-slate-900">${headerTitle}</div>
            <div class="text-xs text-slate-500">AI-guided symptom assessment</div>
          </div>
        </div>
        ${buildTopStatusBadge(messageType, message)}
      </div>
    `;

    if (parsed.intro) {
      contentHTML += buildTextCard(parsed.intro, "text");
    }

    if (parsed.disclaimer) {
      contentHTML += buildInfoSection("Disclaimer", parsed.disclaimer, "blue");
    }

    if (parsed.possibleConcerns.length) {
      contentHTML += buildListSection(
        "Possible Causes",
        parsed.possibleConcerns,
        "indigo",
      );
    }

    if (parsed.warningSigns.length) {
      contentHTML += buildListSection(
        "Warning Signs",
        parsed.warningSigns,
        "amber",
      );
    }

    if (parsed.reported.length) {
      contentHTML += buildListSection(
        "What You Reported",
        parsed.reported,
        "slate",
      );
    }

    if (parsed.summary.length) {
      contentHTML += buildListSection(
        "Assessment Summary",
        parsed.summary,
        "blue",
      );
    }

    if (parsed.specialist.length) {
      contentHTML += buildListSection(
        "Recommended Specialist",
        parsed.specialist,
        "emerald",
      );
    }

    if (parsed.urgency.length) {
      contentHTML += buildUrgencySection(parsed.urgency[0]);
    }

    if (parsed.reasoning.length) {
      contentHTML += buildListSection("Reasoning", parsed.reasoning, "violet");
    }

    if (parsed.nextQuestion) {
      contentHTML += buildQuestionSection(parsed.nextQuestion);
    }

    if (parsed.nextSteps.length) {
      contentHTML += buildListSection("Next Steps", parsed.nextSteps, "cyan");
    }

    if (parsed.other.length) {
      contentHTML += buildListSection(
        "Additional Notes",
        parsed.other,
        "slate",
      );
    }
  } else {
    contentHTML += `
      <div class="flex items-start gap-3">
        <div class="w-9 h-9 rounded-xl ${accentClass} flex items-center justify-center shrink-0 mt-0.5">
          ${getMessageIcon(messageType)}
        </div>
        <div class="text-sm text-slate-700 leading-relaxed">
          ${formatPlainMessage(message)}
        </div>
      </div>
    `;
  }

  const buttonHTML = buildButtonGroup(buttons);

  botMessage.innerHTML = `
    <div class="${wrapperClass}">
      ${contentHTML}
      ${buttonHTML}
    </div>
  `;

  chatMessages.appendChild(botMessage);
  scrollChatToBottom();
}

function parseBotMessageSections(message) {
  const clean = message.replace(/\r/g, "").trim();
  const lines = clean
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const result = {
    isStructured: false,
    intro: "",
    disclaimer: "",
    possibleConcerns: [],
    warningSigns: [],
    reported: [],
    summary: [],
    specialist: [],
    urgency: [],
    reasoning: [],
    nextQuestion: "",
    nextSteps: [],
    other: [],
  };

  let currentSection = "intro";

  for (const line of lines) {
    const plain = line.replace(/\*\*/g, "").trim();

    if (
      plain.toLowerCase().startsWith("⚠️ disclaimer:") ||
      plain.toLowerCase().startsWith("disclaimer:")
    ) {
      result.isStructured = true;
      result.disclaimer = plain
        .replace(/^⚠️\s*/i, "")
        .replace(/^disclaimer:\s*/i, "")
        .trim();
      currentSection = "disclaimer";
      continue;
    }

    if (plain.toLowerCase().includes("possible concerns being considered")) {
      result.isStructured = true;
      currentSection = "possibleConcerns";
      continue;
    }

    if (plain.toLowerCase().includes("possible causes being considered")) {
      result.isStructured = true;
      currentSection = "possibleConcerns";
      continue;
    }

    if (plain.toLowerCase().includes("important warning signs")) {
      result.isStructured = true;
      currentSection = "warningSigns";
      continue;
    }

    if (plain.toLowerCase().includes("warning signs to watch for")) {
      result.isStructured = true;
      currentSection = "warningSigns";
      continue;
    }

    if (plain.toLowerCase().includes("what you reported")) {
      result.isStructured = true;
      currentSection = "reported";
      continue;
    }

    if (plain.toLowerCase().includes("health assessment summary")) {
      result.isStructured = true;
      currentSection = "summary";
      continue;
    }

    if (plain.toLowerCase().includes("assessment summary")) {
      result.isStructured = true;
      currentSection = "summary";
      continue;
    }

    if (plain.toLowerCase().includes("recommended specialist")) {
      result.isStructured = true;
      currentSection = "specialist";
      continue;
    }

    if (plain.toLowerCase().includes("urgency level")) {
      result.isStructured = true;
      currentSection = "urgency";
      continue;
    }

    if (plain.toLowerCase().includes("reasoning summary")) {
      result.isStructured = true;
      currentSection = "reasoning";
      continue;
    }

    if (plain.toLowerCase().startsWith("next question:")) {
      result.isStructured = true;
      result.nextQuestion = plain.replace(/^next question:\s*/i, "").trim();
      currentSection = "nextQuestion";
      continue;
    }

    if (plain.toLowerCase().includes("next steps")) {
      result.isStructured = true;
      currentSection = "nextSteps";
      continue;
    }

    if (plain.toLowerCase().startsWith("why this is urgent:")) {
      result.isStructured = true;
      currentSection = "warningSigns";
      continue;
    }

    if (plain.toLowerCase().startsWith("what to do now:")) {
      result.isStructured = true;
      currentSection = "nextSteps";
      continue;
    }

    if (plain.toLowerCase().startsWith("important:")) {
      result.isStructured = true;
      currentSection = "other";
      continue;
    }

    if (plain.startsWith("-")) {
      const item = plain.replace(/^-+\s*/, "").trim();

      if (currentSection === "possibleConcerns")
        result.possibleConcerns.push(item);
      else if (currentSection === "warningSigns")
        result.warningSigns.push(item);
      else if (currentSection === "reported") result.reported.push(item);
      else if (currentSection === "summary") result.summary.push(item);
      else if (currentSection === "specialist") result.specialist.push(item);
      else if (currentSection === "urgency") result.urgency.push(item);
      else if (currentSection === "reasoning") result.reasoning.push(item);
      else if (currentSection === "nextSteps") result.nextSteps.push(item);
      else result.other.push(item);

      continue;
    }

    if (!result.isStructured && !result.intro) {
      result.intro = plain;
    } else if (currentSection === "intro") {
      result.intro += (result.intro ? " " : "") + plain;
    } else if (currentSection === "other") {
      result.other.push(plain);
    }
  }

  if (
    result.disclaimer ||
    result.possibleConcerns.length ||
    result.warningSigns.length ||
    result.reported.length ||
    result.summary.length ||
    result.specialist.length ||
    result.urgency.length ||
    result.reasoning.length ||
    result.nextQuestion ||
    result.nextSteps.length
  ) {
    result.isStructured = true;
  }

  return result;
}

function buildTextCard(text, variant = "text") {
  let extra = "bg-slate-50 border-slate-200 text-slate-700";
  if (variant === "text") extra = "bg-slate-50 border-slate-200 text-slate-700";

  return `
    <div class="mb-3 rounded-2xl border ${extra} p-3.5">
      <p class="text-sm leading-relaxed">${escapeHtml(text)}</p>
    </div>
  `;
}

function buildInfoSection(title, text, tone = "blue") {
  const styles = {
    blue: "bg-blue-50 border-blue-200 text-blue-900",
    amber: "bg-amber-50 border-amber-200 text-amber-900",
    red: "bg-red-50 border-red-200 text-red-900",
  };

  const cls = styles[tone] || styles.blue;

  return `
    <div class="mb-3 rounded-2xl border ${cls} p-3.5">
      <div class="text-xs font-bold uppercase tracking-wide mb-1">${escapeHtml(title)}</div>
      <div class="text-sm leading-relaxed">${escapeHtml(text)}</div>
    </div>
  `;
}

function buildListSection(title, items, tone = "slate") {
  const tones = {
    slate: "bg-slate-50 border-slate-200",
    indigo: "bg-indigo-50 border-indigo-200",
    amber: "bg-amber-50 border-amber-200",
    blue: "bg-blue-50 border-blue-200",
    emerald: "bg-emerald-50 border-emerald-200",
    violet: "bg-violet-50 border-violet-200",
    cyan: "bg-cyan-50 border-cyan-200",
  };

  const cls = tones[tone] || tones.slate;

  return `
    <div class="mb-3 rounded-2xl border ${cls} p-3.5">
      <div class="text-xs font-bold uppercase tracking-wide text-slate-700 mb-2">${escapeHtml(title)}</div>
      <ul class="space-y-1.5">
        ${items
          .map(
            (item) => `
          <li class="flex items-start gap-2 text-sm text-slate-700 leading-relaxed">
            <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0"></span>
            <span>${escapeHtml(item)}</span>
          </li>
        `,
          )
          .join("")}
      </ul>
    </div>
  `;
}

function buildQuestionSection(question) {
  return `
    <div class="mb-3 rounded-2xl border border-primary/20 bg-primary/5 p-4">
      <div class="text-xs font-bold uppercase tracking-wide text-primary mb-2">Next Question</div>
      <div class="text-sm font-medium text-slate-800 leading-relaxed">${escapeHtml(question)}</div>
    </div>
  `;
}

function buildUrgencySection(urgencyText) {
  const normalized = urgencyText.toLowerCase();
  let badge = buildRiskBadge(normalized);

  return `
    <div class="mb-3 rounded-2xl border border-slate-200 bg-white p-3.5">
      <div class="text-xs font-bold uppercase tracking-wide text-slate-700 mb-2">Urgency</div>
      <div>${badge}</div>
    </div>
  `;
}

function buildTopStatusBadge(messageType, message) {
  if (messageType === "emergency") {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-100 text-red-700 border border-red-200">Emergency</span>`;
  }

  if (messageType === "recommendation") {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-100 text-primary border border-blue-200">Summary</span>`;
  }

  if (message.toLowerCase().includes("next question")) {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-700 border border-amber-200">In Progress</span>`;
  }

  return "";
}

function buildRiskBadge(risk) {
  const value = String(risk).toLowerCase();

  if (value.includes("emergency")) {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-100 text-red-700 border border-red-200">Emergency</span>`;
  }
  if (value.includes("high")) {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-orange-100 text-orange-700 border border-orange-200">High</span>`;
  }
  if (value.includes("medium")) {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-700 border border-amber-200">Medium</span>`;
  }
  if (value.includes("low")) {
    return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">Low</span>`;
  }

  return `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">${escapeHtml(risk)}</span>`;
}

function getMessageIcon(messageType) {
  if (messageType === "emergency") {
    return `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86l-7.5 13A1 1 0 003.66 18h16.68a1 1 0 00.87-1.5l-7.5-13a1 1 0 00-1.74 0z"/>
      </svg>
    `;
  }

  if (messageType === "recommendation") {
    return `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
    `;
  }

  return `
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
    </svg>
  `;
}

function formatPlainMessage(message) {
  return escapeHtml(message)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function buildButtonGroup(buttons) {
  if (!buttons || buttons.length === 0) return "";

  let buttonHTML = `<div class="flex flex-wrap gap-2 mt-4 pt-1">`;

  buttons.forEach((btn) => {
    const action = btn.action;
    const specialty = btn.specialty || "";

    if (action === "browse_doctors") {
      buttonHTML += `
        <a href="doctors.html?specialty=${encodeURIComponent(specialty)}"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-dark transition-colors shadow-sm">
          ${escapeHtml(btn.text)}
        </a>
      `;
    } else if (action === "book_appointment") {
      buttonHTML += `
        <a href="appointments.html?specialty=${encodeURIComponent(specialty)}"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-white border border-primary text-primary text-xs font-semibold rounded-xl hover:bg-blue-50 transition-colors">
          ${escapeHtml(btn.text)}
        </a>
      `;
    } else if (action === "new_assessment") {
      buttonHTML += `
        <button onclick="startConsultation()"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl hover:bg-slate-200 transition-colors">
          ${escapeHtml(btn.text)}
        </button>
      `;
    } else if (action === "emergency_rooms") {
      buttonHTML += `
        <a href="#"
           onclick="alert('This feature is coming soon!'); return false;"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-red-600 text-white text-xs font-semibold rounded-xl hover:bg-red-700 transition-colors shadow-sm">
          ${escapeHtml(btn.text)}
        </a>
      `;
    } else if (action === "call_hotline") {
      buttonHTML += `
        <a href="tel:1-800-CARE-LINK"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-blue-600 text-white text-xs font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm">
          ${escapeHtml(btn.text)}
        </a>
      `;
    } else if (action === "continue") {
      buttonHTML += `
        <button onclick="sendContinueMessage()"
           class="inline-flex items-center justify-center px-4 py-2.5 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-dark transition-colors shadow-sm">
          ${escapeHtml(btn.text)}
        </button>
      `;
    }
  });

  buttonHTML += `</div>`;
  return buttonHTML;
}

function sendContinueMessage() {
  const chatInput = document.getElementById("chatInput");
  if (!chatInput) return;
  chatInput.value = "Continue with assessment";
  sendMessage();
}

function showLoadingMessage(text = "Thinking...") {
  removeLoadingMessage();

  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  loadingMessageEl = document.createElement("div");
  loadingMessageEl.className = "flex justify-start";
  loadingMessageEl.innerHTML = `
    <div class="max-w-[82%] bg-white border border-slate-200 rounded-[24px] rounded-tl-md p-4 shadow-sm">
      <div class="flex items-start gap-3">
        <div class="w-9 h-9 rounded-xl bg-blue-50 text-primary flex items-center justify-center shrink-0">
          <svg class="w-4 h-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
          </svg>
        </div>
        <div class="flex-1">
          <div class="text-sm font-semibold text-slate-900 mb-1">Health Assistant</div>
          <div class="text-sm text-slate-600">${escapeHtml(text)}</div>
          <div class="flex items-center gap-1 mt-3">
            <span class="w-2 h-2 bg-primary/40 rounded-full animate-bounce"></span>
            <span class="w-2 h-2 bg-primary/50 rounded-full animate-bounce [animation-delay:120ms]"></span>
            <span class="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:240ms]"></span>
          </div>
        </div>
      </div>
    </div>
  `;

  chatMessages.appendChild(loadingMessageEl);
  scrollChatToBottom();
}

function removeLoadingMessage() {
  if (loadingMessageEl && loadingMessageEl.parentNode) {
    loadingMessageEl.parentNode.removeChild(loadingMessageEl);
  }
  loadingMessageEl = null;
}

function setWaitingState(waiting) {
  isWaitingForResponse = waiting;

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");

  if (chatInput) chatInput.disabled = waiting;
  if (sendBtn) sendBtn.disabled = waiting;
}

function scrollChatToBottom() {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}
