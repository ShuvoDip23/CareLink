function showAuthAlert(message, type = "error") {
  const alertBox = document.getElementById("alertBox");
  if (!alertBox) return;
  alertBox.className = `alert ${type} show`;
  alertBox.textContent = message;
}

function setLoginRole(role) {
  const roleInput = document.getElementById("loginRole");
  const patientButton = document.getElementById("patientLoginTypeBtn");
  const doctorButton = document.getElementById("doctorLoginTypeBtn");

  if (roleInput) roleInput.value = role;
  patientButton?.classList.toggle("active", role === "patient");
  doctorButton?.classList.toggle("active", role === "doctor");
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("patientLoginTypeBtn")?.addEventListener("click", () => setLoginRole("patient"));
  document.getElementById("doctorLoginTypeBtn")?.addEventListener("click", () => setLoginRole("doctor"));
  setLoginRole("patient");

  const form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = document.getElementById("loginButton");
    const payload = {
      email: document.getElementById("email").value.trim(),
      password: document.getElementById("password").value,
    };

    button.disabled = true;
    button.textContent = "Signing in...";

    try {
      const response = await apiFetch("/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Login failed");
      }

      localStorage.setItem("user", JSON.stringify(data.user));
      showAuthAlert("Login successful. Redirecting...", "success");

      setTimeout(() => {
        window.location.href = data.user.role === "admin" ? "admin_add_doctor.html" : "index.html";
      }, 700);
    } catch (error) {
      showAuthAlert(error.message || "Network error. Please check the backend.");
      button.disabled = false;
      button.textContent = "Sign in";
    }
  });
});
