// API Base URL
const API_BASE_URL = "http://localhost:5000/api";

// Utility function to get or create user ID
function getUserId() {
  let userId = localStorage.getItem("carelink_user_id");
  if (!userId) {
    userId =
      "user_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    localStorage.setItem("carelink_user_id", userId);
  }
  return userId;
}

// Utility function to format date
function formatDate(dateString) {
  const options = { year: "numeric", month: "long", day: "numeric" };
  return new Date(dateString).toLocaleDateString(undefined, options);
}

// Utility function to show/hide loading spinner
function showLoading() {
  const spinner = document.getElementById("loadingSpinner");
  if (spinner) spinner.style.display = "block";
}

function hideLoading() {
  const spinner = document.getElementById("loadingSpinner");
  if (spinner) spinner.style.display = "none";
}

// Set minimum date for appointment booking (today)
function setMinDate() {
  const dateInput = document.getElementById("appointmentDate");
  if (dateInput) {
    const today = new Date().toISOString().split("T")[0];
    dateInput.setAttribute("min", today);
  }
}

// Initialize date picker on page load
document.addEventListener("DOMContentLoaded", function () {
  setMinDate();
});

// Chatbot functions (referenced from HTML but defined in chat.js)
function openChatbot() {
  const chatWidget = document.getElementById("chatWidget");
  const floatBtn = document.getElementById("chatFloatBtn");
  if (chatWidget && floatBtn) {
    chatWidget.classList.add("active");
    floatBtn.style.display = "none";
  }
}

function closeChatbot() {
  const chatWidget = document.getElementById("chatWidget");
  const floatBtn = document.getElementById("chatFloatBtn");
  if (chatWidget && floatBtn) {
    chatWidget.classList.remove("active");
    floatBtn.style.display = "flex";
  }
}

function toggleChatbot() {
  const chatWidget = document.getElementById("chatWidget");
  if (chatWidget.classList.contains("active")) {
    closeChatbot();
  } else {
    openChatbot();
  }
}
