const API_URL = "http://127.0.0.1:5000";

let currentSessionId = null;
let currentDbSessionId = null;
let isAuthenticated = false;

document.addEventListener("DOMContentLoaded", async () => {
  await checkChatAuth();

  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter" && !this.disabled) {
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
    <div class="flex flex-col items-center justify-center h-full p-8 text-center">
      <svg class="w-16 h-16 text-primary mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
      </svg>
      <h3 class="text-lg font-semibold text-slate-900 mb-2">Login Required</h3>
      <p class="text-slate-600 mb-6">Please login to use the Health Assistant and save your chat history.</p>
      <div class="flex gap-3">
        <a href="login.html" class="px-6 py-2.5 bg-primary text-white font-semibold rounded-lg hover:bg-primary-dark transition-colors">
          Login
        </a>
        <a href="register.html" class="px-6 py-2.5 bg-white border-2 border-gray-300 text-slate-700 font-semibold rounded-lg hover:border-primary hover:text-primary transition-colors">
          Sign Up
        </a>
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
    <div class="flex flex-col gap-4">
      <div class="flex">
        <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[85%]">
          <p class="text-sm text-slate-700">
            Welcome back! You can start a new consultation or open one of your previous chats.
          </p>
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
    const response = await fetch(`${API_URL}/api/session/start`, {
      method: "POST",
      credentials: "include",
    });

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
    console.error("Failed to start consultation:", error);
    addBotMessage(
      "Sorry, I encountered an error. Please try again or check if you're logged in.",
    );
  }
}

async function sendMessage() {
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");

  if (!chatInput || !chatMessages || !currentDbSessionId) return;

  const message = chatInput.value.trim();
  if (message === "") return;

  addUserMessage(message);
  chatInput.value = "";

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

    if (response.status === 401) {
      showLoginPrompt();
      return;
    }

    const data = await response.json();
    addBotMessage(data.message, data.message_type, data.buttons);
  } catch (error) {
    console.error("Failed to send message:", error);
    addBotMessage("Sorry, I encountered an error. Please try again.");
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
    const response = await fetch(`${API_URL}/api/chat/history`, {
      method: "GET",
      credentials: "include",
    });

    if (response.status === 401) {
      showLoginPrompt();
      return;
    }

    const data = await response.json();
    const history = data.history || [];

    if (history.length === 0) {
      chatMessages.innerHTML = `
        <div class="flex">
          <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[85%]">
            <p class="text-sm text-slate-700">You do not have any previous chat history yet.</p>
          </div>
        </div>
      `;
      if (startBtn) startBtn.style.display = "block";
      if (chatInput) chatInput.disabled = true;
      if (sendBtn) sendBtn.disabled = true;
      return;
    }

    let html = `
      <div class="flex">
        <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-sm w-full">
          <p class="text-sm font-semibold text-slate-900 mb-3">Previous Chats</p>
          <div class="flex flex-col gap-2">
    `;

    history.forEach((item) => {
      const session = item.session;
      const dateText = new Date(session.started_at).toLocaleString();
      const risk = session.risk_level || "unknown";
      const specialty = session.recommended_specialty || "Not assigned";

      html += `
        <button onclick="loadSessionMessages(${session.id})"
          class="text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
          <div class="text-sm font-semibold text-slate-900">${dateText}</div>
          <div class="text-xs text-slate-600 mt-1">Risk: ${escapeHtml(risk)} | Specialist: ${escapeHtml(specialty)}</div>
        </button>
      `;
    });

    html += `
          </div>
        </div>
      </div>
    `;

    chatMessages.innerHTML = html;

    if (startBtn) startBtn.style.display = "block";
    if (chatInput) chatInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
  } catch (error) {
    console.error("Failed to load history:", error);
    addBotMessage("Sorry, I could not load your chat history.");
  }
}

async function loadSessionMessages(sessionId) {
  const chatMessages = document.getElementById("chatMessages");
  const startBtn = document.getElementById("startBtn");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");

  try {
    const response = await fetch(`${API_URL}/api/chat/session/${sessionId}`, {
      method: "GET",
      credentials: "include",
    });

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
    console.error("Failed to load session messages:", error);
    addBotMessage("Sorry, I could not load that previous chat.");
  }
}

function addUserMessage(message) {
  const chatMessages = document.getElementById("chatMessages");

  const userMessage = document.createElement("div");
  userMessage.className = "flex justify-end";
  userMessage.innerHTML = `
    <div class="bg-primary text-white rounded-2xl rounded-tr-none p-4 shadow-sm max-w-[80%]">
      <p class="text-sm">${escapeHtml(message)}</p>
    </div>
  `;
  chatMessages.appendChild(userMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBotMessage(message, messageType = "text", buttons = null) {
  const chatMessages = document.getElementById("chatMessages");

  let formattedMessage = message
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");

  let messageClass =
    "bg-white rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]";
  let textClass = "text-sm text-slate-700";

  if (messageType === "emergency" || messageType === "context_warning") {
    messageClass =
      "bg-red-50 border-2 border-red-200 rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]";
    textClass = "text-sm text-red-900";
  } else if (messageType === "recommendation") {
    messageClass =
      "bg-blue-50 border-2 border-blue-200 rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]";
    textClass = "text-sm text-blue-900";
  }

  const botMessage = document.createElement("div");
  botMessage.className = "flex flex-col";

  let buttonHTML = "";
  if (buttons && buttons.length > 0) {
    buttonHTML = '<div class="flex flex-wrap gap-2 mt-3">';
    buttons.forEach((btn) => {
      const action = btn.action;
      const specialty = btn.specialty || "";

      if (action === "browse_doctors") {
        buttonHTML += `
          <a href="doctors.html?specialty=${encodeURIComponent(specialty)}" 
             class="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-primary-dark transition-colors">
            ${escapeHtml(btn.text)}
          </a>
        `;
      } else if (action === "book_appointment") {
        buttonHTML += `
          <a href="appointments.html?specialty=${encodeURIComponent(specialty)}" 
             class="px-4 py-2 bg-white border-2 border-primary text-primary text-xs font-semibold rounded-lg hover:bg-blue-50 transition-colors">
            ${escapeHtml(btn.text)}
          </a>
        `;
      } else if (action === "new_assessment") {
        buttonHTML += `
          <button onclick="startConsultation()" 
             class="px-4 py-2 bg-gray-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-gray-200 transition-colors">
            ${escapeHtml(btn.text)}
          </button>
        `;
      } else if (action === "emergency_rooms") {
        buttonHTML += `
          <a href="#" onclick="alert('This feature is coming soon!'); return false;"
             class="px-4 py-2 bg-red-600 text-white text-xs font-semibold rounded-lg hover:bg-red-700 transition-colors">
            ${escapeHtml(btn.text)}
          </a>
        `;
      } else if (action === "call_hotline") {
        buttonHTML += `
          <a href="tel:1-800-CARE-LINK" 
             class="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            ${escapeHtml(btn.text)}
          </a>
        `;
      } else if (action === "continue") {
        buttonHTML += `
          <button onclick="sendContinueMessage()" 
             class="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-primary-dark transition-colors">
            ${escapeHtml(btn.text)}
          </button>
        `;
      }
    });
    buttonHTML += "</div>";
  }

  botMessage.innerHTML = `
    <div class="${messageClass}">
      <p class="${textClass}">${formattedMessage}</p>
      ${buttonHTML}
    </div>
  `;

  chatMessages.appendChild(botMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendContinueMessage() {
  const chatInput = document.getElementById("chatInput");
  chatInput.value = "Continue with assessment";
  sendMessage();
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
