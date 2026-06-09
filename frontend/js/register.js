function showRegisterAlert(message, type = "error") {
  const alertBox = document.getElementById("alertBox");
  if (!alertBox) return;
  alertBox.className = `alert ${type} show`;
  alertBox.textContent = message;
}

function setAccountType(type) {
  const accountType = document.getElementById("accountType");
  const doctorFields = document.getElementById("doctorFields");
  const patientButton = document.getElementById("patientTypeBtn");
  const doctorButton = document.getElementById("doctorTypeBtn");
  const isDoctor = type === "doctor";

  accountType.value = type;
  doctorFields.style.display = isDoctor ? "grid" : "none";
  patientButton.classList.toggle("active", !isDoctor);
  doctorButton.classList.toggle("active", isDoctor);

  doctorFields.querySelectorAll("input, textarea").forEach((field) => {
    field.required = isDoctor;
  });
}

function buildRegisterPayload() {
  const accountType = document.getElementById("accountType").value;
  const payload = {
    account_type: accountType,
    name: document.getElementById("name").value.trim(),
    email: document.getElementById("email").value.trim(),
    password: document.getElementById("password").value,
  };

  if (accountType === "doctor") {
    payload.specialty = document.getElementById("specialty").value.trim();
    payload.hospital = document.getElementById("hospital").value.trim();
    payload.location = document.getElementById("location").value.trim();
    payload.phone = document.getElementById("phone").value.trim();
    payload.fee = document.getElementById("fee").value;
    payload.qualification = document.getElementById("qualification").value.trim();
    payload.experience_years = document.getElementById("experienceYears").value;
  }

  return payload;
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("patientTypeBtn")?.addEventListener("click", () => setAccountType("patient"));
  document.getElementById("doctorTypeBtn")?.addEventListener("click", () => setAccountType("doctor"));
  setAccountType("patient");

  const form = document.getElementById("registerForm");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    const accountType = document.getElementById("accountType").value;
    const button = document.getElementById("registerButton");

    if (password.length < 6) {
      showRegisterAlert("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      showRegisterAlert("Passwords do not match.");
      return;
    }

    button.disabled = true;
    button.textContent = accountType === "doctor" ? "Submitting profile..." : "Creating account...";

    try {
      const response = await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify(buildRegisterPayload()),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Registration failed");
      }

      localStorage.setItem("user", JSON.stringify(data.user));

      if (accountType === "doctor") {
        showRegisterAlert("Doctor profile submitted. It will appear publicly after admin approval.", "success");
      } else {
        showRegisterAlert("Account created successfully. Redirecting...", "success");
      }

      setTimeout(() => {
        window.location.href = "index.html";
      }, 900);
    } catch (error) {
      showRegisterAlert(error.message || "Network error. Please check the backend.");
      button.disabled = false;
      button.textContent = "Create account";
    }
  });
});
