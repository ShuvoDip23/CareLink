const API_ORIGIN = "http://127.0.0.1:5000";
const API_BASE_URL = `${API_ORIGIN}/api`;

window.API_ORIGIN = API_ORIGIN;
window.API_BASE_URL = API_BASE_URL;

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const hasBody = Boolean(options.body);

  return fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: hasBody
      ? { "Content-Type": "application/json", ...headers }
      : headers,
  });
}

async function getJson(path, options = {}) {
  const response = await apiFetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function normalizeUser(user) {
  if (!user) return null;
  return {
    ...user,
    role: user.role || "patient",
  };
}

async function checkAuthAndUpdateUI() {
  let user = null;

  try {
    const data = await getJson("/me");
    if (data.authenticated) {
      user = normalizeUser(data.user);
      localStorage.setItem("user", JSON.stringify(user));
    } else {
      localStorage.removeItem("user");
    }
  } catch (error) {
    user = getCurrentUser();
  }

  if (user) {
    showLoggedInUI(user);
  } else {
    showLoggedOutUI();
  }

  return user;
}

function setNavVisible(id, visible) {
  const element = document.getElementById(id);
  if (!element) return;
  element.style.display = visible ? "" : "none";
}

function showLoggedInUI(user) {
  const normalizedUser = normalizeUser(user);
  const isPatient = !normalizedUser.role || normalizedUser.role === "patient";
  const isAdmin = normalizedUser.role === "admin";

  setNavVisible("navLogin", false);
  setNavVisible("navRegister", false);
  setNavVisible("navAppointments", isPatient);
  setNavVisible("navAdmin", isAdmin);
  setNavVisible("navUser", true);
  setNavVisible("navLogout", true);

  const navUser = document.getElementById("navUser");
  if (navUser) {
    navUser.innerHTML = `
      <span class="user-chip" title="${escapeHtml(normalizedUser.name)}">
        <span class="user-chip-avatar">${escapeHtml(getInitials(normalizedUser.name))}</span>
        <span class="user-chip-name">${escapeHtml(normalizedUser.name)}</span>
      </span>
    `;
  }
}

function showLoggedOutUI() {
  setNavVisible("navLogin", true);
  setNavVisible("navRegister", true);
  setNavVisible("navAppointments", false);
  setNavVisible("navAdmin", false);
  setNavVisible("navUser", false);
  setNavVisible("navLogout", false);
}

async function logoutUser() {
  try {
    await apiFetch("/logout", { method: "POST" });
  } catch (error) {
    console.error("Logout request failed:", error);
  } finally {
    localStorage.removeItem("user");
    window.location.href = "index.html";
  }
}

function getCurrentUser() {
  try {
    return normalizeUser(JSON.parse(localStorage.getItem("user")));
  } catch (error) {
    localStorage.removeItem("user");
    return null;
  }
}

function getUserId() {
  const user = getCurrentUser();
  return user ? user.id : null;
}

function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text ?? "").replace(/[&<>"']/g, (m) => map[m]);
}

function getInitials(name) {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) return "CL";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function formatDate(dateString) {
  if (!dateString) return "Not set";
  return new Date(`${dateString}T00:00:00`).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(dateString) {
  if (!dateString) return "";
  return new Date(dateString).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatFee(fee) {
  const value = Number(fee || 0);
  const formatted = Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : "0";
  return `\u09F3${formatted}`;
}

function renderStars(rating = 5) {
  const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
  const fullStars = Math.round(safeRating);
  return Array.from({ length: 5 })
    .map((_, index) => {
      const filled = index < fullStars;
      return `<svg viewBox="0 0 20 20" aria-hidden="true" class="${filled ? "star-filled" : "star-muted"}"><path d="M10 1.7l2.4 5 5.5.8-4 3.9.9 5.5L10 14.3l-4.9 2.6.9-5.5-4-3.9 5.5-.8L10 1.7z"/></svg>`;
    })
    .join("");
}

function renderDoctorIcon() {
  return svgIcon("stethoscope");
}

let revealObserver = null;

function observeRevealElements(root = document) {
  if (!revealObserver) return;
  root.querySelectorAll(".reveal:not(.visible)").forEach((element) => {
    revealObserver.observe(element);
  });
}

function setupRevealAnimations() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  document
    .querySelectorAll(
      ".hero-grid > *, .trust-item, .feature-item, .search-panel, .doctor-info-card, .booking-card, .dashboard-panel, .admin-panel, .auth-card, .footer-content > *",
    )
    .forEach((element) => element.classList.add("reveal"));

  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -36px 0px" },
  );

  observeRevealElements();
}

function setupHeroSlotInteraction(root = document) {
  root.querySelectorAll(".hero-slot").forEach((slot) => {
    slot.addEventListener("click", () => {
      const stage = slot.closest(".hero-visual-stage") || document;
      stage.querySelectorAll(".hero-slot").forEach((item) => item.classList.remove("active"));
      slot.classList.add("active");
    });
  });
}

function showLoading() {
  const spinner = document.getElementById("loadingSpinner");
  if (spinner) spinner.style.display = "block";
}

function hideLoading() {
  const spinner = document.getElementById("loadingSpinner");
  if (spinner) spinner.style.display = "none";
}

let emergencyState = {
  user: null,
  providers: [],
  selectedProvider: null,
  distanceKm: null,
  latitude: null,
  longitude: null,
  summary: "",
};

function setupEmergencyAssist(user) {
  emergencyState.user = normalizeUser(user);
  const existingButton = document.getElementById("emergencySosButton");
  const existingModal = document.getElementById("emergencyAssistModal");

  if (!emergencyState.user || emergencyState.user.role !== "patient") {
    if (existingButton) existingButton.remove();
    if (existingModal) existingModal.remove();
    return;
  }

  if (!existingButton) {
    const button = document.createElement("button");
    button.id = "emergencySosButton";
    button.className = "sos-float-btn";
    button.type = "button";
    button.setAttribute("aria-label", "Open Emergency Assist");
    button.innerHTML = `
      <span class="sos-pulse" aria-hidden="true"></span>
      <strong>SOS</strong>
      <span>Emergency Assist</span>
    `;
    button.addEventListener("click", openEmergencyAssist);
    document.body.appendChild(button);
  }

  if (!existingModal) {
    const modal = document.createElement("div");
    modal.id = "emergencyAssistModal";
    modal.className = "emergency-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="emergency-modal-panel" role="dialog" aria-modal="true" aria-labelledby="emergencyAssistTitle">
        <div class="emergency-modal-header">
          <div>
            <span class="emergency-kicker">Patient safety</span>
            <h2 id="emergencyAssistTitle">Emergency Assist</h2>
          </div>
          <button type="button" class="emergency-close" id="emergencyCloseButton" aria-label="Close Emergency Assist">&times;</button>
        </div>

        <div class="emergency-warning">
          <strong>Emergency warning</strong>
          <span>If symptoms are severe or life-threatening, call local emergency services or go to the nearest emergency department now. CareLink does not diagnose.</span>
        </div>

        <div id="emergencyStatus" class="emergency-status">Requesting your location...</div>

        <div id="emergencyFallback" class="emergency-fallback hidden">
          <label for="emergencyZoneSelect">Choose a Rajshahi zone</label>
          <select id="emergencyZoneSelect">
            <option value="">Show all listed providers</option>
          </select>
          <div id="emergencyProviderList" class="emergency-provider-list"></div>
        </div>

        <div id="emergencyProviderCard" class="emergency-provider-card hidden"></div>

        <div class="emergency-summary-wrap">
          <div class="emergency-summary-head">
            <h3>Emergency summary</h3>
            <span>Generated from CareLink history, not a diagnosis.</span>
          </div>
          <pre id="emergencySummaryBox" class="emergency-summary-box">Preparing summary...</pre>
        </div>

        <div class="emergency-actions">
          <a id="emergencyCallButton" class="btn btn-danger hidden" href="#">${svgIcon("phone")} Call Provider</a>
          <button type="button" class="btn btn-secondary" id="copyEmergencySummaryButton">Copy Summary</button>
          <button type="button" class="btn btn-primary" id="shareEmergencySummaryButton">Share Summary</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById("emergencyCloseButton").addEventListener("click", closeEmergencyAssist);
    document.getElementById("copyEmergencySummaryButton").addEventListener("click", copyEmergencySummary);
    document.getElementById("shareEmergencySummaryButton").addEventListener("click", shareEmergencySummary);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeEmergencyAssist();
    });
  }
}

async function openEmergencyAssist() {
  const modal = document.getElementById("emergencyAssistModal");
  if (!modal) return;
  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
  resetEmergencyModal();

  try {
    emergencyState.providers = await getJson("/emergency/providers");
    populateEmergencyZones();
  } catch (error) {
    setEmergencyStatus(error.message || "Could not load emergency providers.", true);
    return;
  }

  requestEmergencyLocation();
  await loadEmergencySummary();
}

function closeEmergencyAssist() {
  const modal = document.getElementById("emergencyAssistModal");
  if (!modal) return;
  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
}

function resetEmergencyModal() {
  emergencyState.selectedProvider = null;
  emergencyState.distanceKm = null;
  emergencyState.latitude = null;
  emergencyState.longitude = null;
  emergencyState.summary = "";
  setEmergencyStatus("Requesting your location...");
  document.getElementById("emergencyFallback")?.classList.add("hidden");
  document.getElementById("emergencyProviderCard")?.classList.add("hidden");
  document.getElementById("emergencyCallButton")?.classList.add("hidden");
  const summaryBox = document.getElementById("emergencySummaryBox");
  if (summaryBox) summaryBox.textContent = "Preparing summary...";
}

function setEmergencyStatus(message, isError = false) {
  const status = document.getElementById("emergencyStatus");
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("error", Boolean(isError));
}

function requestEmergencyLocation() {
  if (!navigator.geolocation) {
    showEmergencyFallback("Location is not available in this browser. Choose a Rajshahi zone below.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      emergencyState.latitude = position.coords.latitude;
      emergencyState.longitude = position.coords.longitude;
      setEmergencyStatus("Finding the nearest listed emergency provider...");
      await loadNearestEmergencyProvider(emergencyState.latitude, emergencyState.longitude);
    },
    () => showEmergencyFallback("Location permission was denied. Choose a Rajshahi zone or view all listed providers."),
    { enableHighAccuracy: true, timeout: 9000, maximumAge: 60000 },
  );
}

async function loadNearestEmergencyProvider(latitude, longitude) {
  try {
    const result = await getJson("/emergency/nearest", {
      method: "POST",
      body: JSON.stringify({ latitude, longitude }),
    });
    emergencyState.selectedProvider = result.provider;
    emergencyState.distanceKm = result.distance_km;
    renderEmergencyProviderCard(result.provider, result.distance_km);
    setEmergencyStatus("Nearest listed emergency provider found.");
    await saveEmergencyAlert();
  } catch (error) {
    showEmergencyFallback(error.message || "Could not calculate nearest provider. Choose a Rajshahi zone below.");
  }
}

async function loadEmergencySummary() {
  try {
    const result = await getJson("/emergency/summary", {
      method: "POST",
      body: JSON.stringify({}),
    });
    emergencyState.summary = result.summary;
    const summaryBox = document.getElementById("emergencySummaryBox");
    if (summaryBox) summaryBox.textContent = result.summary;
    await saveEmergencyAlert();
  } catch (error) {
    const message = error.message || "Could not generate emergency summary.";
    emergencyState.summary = message;
    const summaryBox = document.getElementById("emergencySummaryBox");
    if (summaryBox) summaryBox.textContent = message;
  }
}

async function saveEmergencyAlert() {
  if (
    !emergencyState.summary ||
    !emergencyState.selectedProvider ||
    emergencyState.latitude === null ||
    emergencyState.longitude === null
  ) {
    return;
  }

  try {
    await getJson("/emergency/alert", {
      method: "POST",
      body: JSON.stringify({
        latitude: emergencyState.latitude,
        longitude: emergencyState.longitude,
        nearest_provider_id: emergencyState.selectedProvider.id,
        summary: emergencyState.summary,
      }),
    });
  } catch (error) {
    console.warn("Could not save emergency alert:", error);
  }
}

function populateEmergencyZones() {
  const select = document.getElementById("emergencyZoneSelect");
  if (!select) return;

  const zones = [...new Set(emergencyState.providers.map((provider) => provider.zone))];
  select.innerHTML = '<option value="">Show all listed providers</option>';
  zones.forEach((zone) => {
    const option = document.createElement("option");
    option.value = zone;
    option.textContent = zone;
    select.appendChild(option);
  });

  select.onchange = () => renderEmergencyProviderList(select.value);
}

function showEmergencyFallback(message) {
  setEmergencyStatus(message);
  document.getElementById("emergencyFallback")?.classList.remove("hidden");
  renderEmergencyProviderList("");
}

function renderEmergencyProviderList(zone) {
  const list = document.getElementById("emergencyProviderList");
  if (!list) return;

  const providers = zone
    ? emergencyState.providers.filter((provider) => provider.zone === zone)
    : emergencyState.providers;

  list.innerHTML = providers.map((provider) => `
    <button type="button" class="emergency-provider-option" data-provider-id="${provider.id}">
      <strong>${escapeHtml(provider.name)}</strong>
      <span>${escapeHtml(provider.zone)}</span>
      <small>${escapeHtml(provider.address)}</small>
    </button>
  `).join("");

  list.querySelectorAll("[data-provider-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const provider = emergencyState.providers.find((item) => item.id === Number(button.dataset.providerId));
      if (!provider) return;
      emergencyState.selectedProvider = provider;
      emergencyState.distanceKm = null;
      emergencyState.latitude = provider.latitude;
      emergencyState.longitude = provider.longitude;
      renderEmergencyProviderCard(provider, null);
      setEmergencyStatus("Provider selected from Rajshahi zone list.");
      saveEmergencyAlert();
    });
  });
}

function renderEmergencyProviderCard(provider, distanceKm) {
  const card = document.getElementById("emergencyProviderCard");
  const callButton = document.getElementById("emergencyCallButton");
  if (!card || !provider) return;

  card.classList.remove("hidden");
  card.innerHTML = `
    <div class="emergency-provider-icon">${svgIcon("map")}</div>
    <div>
      <div class="emergency-provider-topline">
        <span>${escapeHtml(provider.zone)}</span>
        <strong>${provider.available_24_7 ? "24/7 listed" : "Limited hours"}</strong>
      </div>
      <h3>${escapeHtml(provider.name)}</h3>
      <p>${escapeHtml(provider.address)}</p>
      <div class="emergency-provider-meta">
        <span>${escapeHtml(provider.phone)}</span>
        ${distanceKm !== null && distanceKm !== undefined ? `<span>${distanceKm} km away</span>` : "<span>Manual zone selection</span>"}
      </div>
    </div>
  `;

  if (callButton) {
    callButton.href = `tel:${provider.phone}`;
    callButton.classList.remove("hidden");
  }
}

async function copyEmergencySummary() {
  const text = emergencyState.summary || document.getElementById("emergencySummaryBox")?.textContent || "";
  if (!text.trim()) return;
  await navigator.clipboard.writeText(text);
  setEmergencyStatus("Emergency summary copied.");
}

async function shareEmergencySummary() {
  const text = emergencyState.summary || document.getElementById("emergencySummaryBox")?.textContent || "";
  if (!text.trim()) return;

  if (navigator.share) {
    try {
      await navigator.share({
        title: "CareLink Emergency Summary",
        text,
      });
      setEmergencyStatus("Emergency summary shared.");
      return;
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }

  await copyEmergencySummary();
}

function setMinDate() {
  const dateInput = document.getElementById("appointmentDate");
  if (!dateInput) return;
  const today = new Date().toISOString().split("T")[0];
  dateInput.setAttribute("min", today);
}

function setupMobileNavbar() {
  const toggle = document.getElementById("navToggle");
  const menu = document.getElementById("navMenu");
  if (!toggle || !menu) return;

  toggle.addEventListener("click", () => {
    const isOpen = menu.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    });
  });
}

function renderPlatformPreview(target) {
  target.innerHTML = `
    <span class="hero-ring"></span>
    <span class="hero-ring secondary"></span>
    <article class="doctor-hero-card">
      <div class="hero-card-header">
        <div class="doctor-visual-head">
          <span class="hero-doctor-icon">${renderDoctorIcon()}</span>
          <div>
            <h3 class="hero-doc-name">Dr. Amina Rahman</h3>
            <p class="hero-doc-spec">Cardiology Specialist</p>
          </div>
        </div>
        <span class="availability-badge">Available</span>
      </div>
      <div class="rating-line" aria-label="4.9 out of 5 rating">
        <span class="stars">${renderStars(4.9)}</span>
        <span>4.9 patient rating</span>
      </div>
      <div class="hero-slot-grid" style="margin-top:20px;">
        <button class="hero-slot active" type="button">09:00</button>
        <button class="hero-slot" type="button">11:30</button>
        <button class="hero-slot" type="button">03:00</button>
      </div>
      <a href="doctors.html" class="btn btn-primary btn-block" style="margin-top:20px;">View Doctors</a>
    </article>
    <aside class="appointment-float-card">
      <div class="mini-card-inner">
        <span class="mini-icon">${svgIcon("check")}</span>
        <div>
          <div class="mini-title">Appointment Confirmed</div>
          <div class="mini-sub">Today at 11:30 AM</div>
        </div>
      </div>
    </aside>
  `;
  setupHeroSlotInteraction(target);
}

function renderUpcomingAppointment(target, appointment) {
  target.innerHTML = `
    <span class="hero-ring"></span>
    <span class="hero-ring secondary"></span>
    <article class="doctor-hero-card">
      <div class="hero-card-header">
        <div class="doctor-visual-head">
          <span class="hero-doctor-icon">${renderDoctorIcon()}</span>
          <div>
            <h3 class="hero-doc-name">${escapeHtml(appointment.doctor_name || "Doctor")}</h3>
            <p class="hero-doc-spec">${escapeHtml(appointment.doctor_specialty || "Medical specialist")}</p>
          </div>
        </div>
        <span class="availability-badge">Confirmed</span>
      </div>
      <div class="rating-line">
        <span class="stars">${renderStars(4.8)}</span>
        <span>Trusted specialist</span>
      </div>
      <div class="preview-meta-row" style="margin-top:20px;">
        <span>${svgIcon("calendar")} ${formatDate(appointment.appointment_date)}</span>
        <span>${svgIcon("clock")} ${escapeHtml(appointment.appointment_time)}</span>
      </div>
      <a href="appointments.html" class="btn btn-primary btn-block" style="margin-top:20px;">View Appointment</a>
    </article>
    <aside class="appointment-float-card">
      <div class="mini-card-inner">
        <span class="mini-icon">${svgIcon("check")}</span>
        <div>
          <div class="mini-title">Appointment Confirmed</div>
          <div class="mini-sub">${formatDate(appointment.appointment_date)} at ${escapeHtml(appointment.appointment_time)}</div>
        </div>
      </div>
    </aside>
  `;
  setupHeroSlotInteraction(target);
}

async function initHomepagePreview(user) {
  const target = document.getElementById("homePreviewCard");
  if (!target) return;

  const normalizedUser = normalizeUser(user);
  if (!normalizedUser || normalizedUser.role !== "patient") {
    renderPlatformPreview(target);
    return;
  }

  try {
    const appointments = await getJson("/appointments");
    const upcoming = appointments
      .filter((appointment) => appointment.is_upcoming === true)
      .sort((a, b) => `${a.appointment_date} ${a.appointment_time}`.localeCompare(`${b.appointment_date} ${b.appointment_time}`))[0];

    if (upcoming) {
      renderUpcomingAppointment(target, upcoming);
    } else {
      renderPlatformPreview(target);
    }
  } catch (error) {
    renderPlatformPreview(target);
  }
}

function svgIcon(name) {
  const icons = {
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    heart: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>',
    search: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 21-4.3-4.3M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3v4M16 3v4M4 9h16M6 5h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"/></svg>',
    clock: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>',
    shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.4 2.8 8.4 7 10 4.2-1.6 7-5.6 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></svg>',
    stethoscope: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4v5a4 4 0 0 0 8 0V4M4 4h4M12 4h4M10 14v1a5 5 0 0 0 10 0v-2"/><circle cx="20" cy="10" r="2"/></svg>',
    map: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    phone: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.4 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/></svg>',
    check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m20 6-11 11-5-5"/></svg>',
  };

  return icons[name] || icons.check;
}

document.addEventListener("DOMContentLoaded", async () => {
  setupMobileNavbar();
  setupRevealAnimations();
  setupHeroSlotInteraction();
  setMinDate();
  const user = await checkAuthAndUpdateUI();
  setupEmergencyAssist(user);
  await initHomepagePreview(user);
  observeRevealElements();
});
