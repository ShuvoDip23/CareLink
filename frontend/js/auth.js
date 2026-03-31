// Auth Helper Functions
const API_URL = "http://127.0.0.1:5000";

// Check if user is authenticated
async function checkAuth() {
  try {
    const response = await fetch(`${API_URL}/api/me`, {
      method: "GET",
      credentials: "include",
    });

    const data = await response.json();

    if (data.authenticated) {
      localStorage.setItem("user", JSON.stringify(data.user));
      return data.user;
    } else {
      localStorage.removeItem("user");
      return null;
    }
  } catch (error) {
    console.error("Auth check failed:", error);
    return null;
  }
}

// Logout function
async function logout() {
  try {
    await fetch(`${API_URL}/api/logout`, {
      method: "POST",
      credentials: "include",
    });

    localStorage.removeItem("user");
    window.location.href = "login.html";
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Get current user from localStorage
function getCurrentUser() {
  const userStr = localStorage.getItem("user");
  return userStr ? JSON.parse(userStr) : null;
}

// Update navbar based on auth status
async function updateNavbar() {
  const user = await checkAuth();
  const navbar = document.querySelector("nav");

  if (!navbar) return;

  // Find the nav links container
  const navLinks = navbar.querySelector(".nav-menu, ul");

  if (!navLinks) return;

  // Remove existing auth links
  const existingAuthLinks = navLinks.querySelectorAll(".auth-link");
  existingAuthLinks.forEach((link) => link.remove());

  if (user) {
    // User is logged in - show logout and profile
    const profileLi = document.createElement("li");
    profileLi.className = "auth-link";
    profileLi.innerHTML = `
            <span class="text-sm font-medium text-slate-600">
                ${user.name}
            </span>
        `;
    navLinks.appendChild(profileLi);

    const logoutLi = document.createElement("li");
    logoutLi.className = "auth-link";
    logoutLi.innerHTML = `
            <a href="#" onclick="logout(); return false;" class="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
                Logout
            </a>
        `;
    navLinks.appendChild(logoutLi);
  } else {
    // User is not logged in - show login and register
    const loginLi = document.createElement("li");
    loginLi.className = "auth-link";
    loginLi.innerHTML = `
            <a href="login.html" class="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
                Login
            </a>
        `;
    navLinks.appendChild(loginLi);

    const registerLi = document.createElement("li");
    registerLi.className = "auth-link";
    registerLi.innerHTML = `
            <a href="register.html" class="text-sm font-medium text-white bg-primary hover:bg-primary-dark px-4 py-2 rounded-lg transition-colors">
                Sign Up
            </a>
        `;
    navLinks.appendChild(registerLi);
  }
}

// Initialize auth on page load
document.addEventListener("DOMContentLoaded", () => {
  updateNavbar();
});
