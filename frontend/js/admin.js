let editingDoctorId = null;
let adminDoctors = [];

const availabilityDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const availabilitySlots = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"];

function showAdminAlert(message, type = "success") {
  const alertBox = document.getElementById("adminAlert");
  if (!alertBox) return;
  alertBox.className = `alert ${type} show`;
  alertBox.textContent = message;
}

function doctorExperienceLabel(doctor) {
  const years = Number(doctor.experience_years || 0);
  return years > 0 ? `${years} years` : "Experience not updated";
}

function defaultAvailabilityForSpecialty(specialty) {
  const normalized = String(specialty || "").toLowerCase();
  if (normalized.includes("cardiologist")) return ["09:00 AM", "10:00 AM", "11:00 AM"];
  if (normalized.includes("dermatologist")) return ["12:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"];
  if (normalized.includes("ent specialist")) return ["11:00 AM", "12:00 PM", "04:00 PM", "05:00 PM"];
  return availabilitySlots;
}

function renderAvailabilityEditor(selectedByDay = null) {
  const editor = document.getElementById("availabilityEditor");
  if (!editor) return;

  const fallbackSlots = defaultAvailabilityForSpecialty(document.getElementById("doctorSpecialty")?.value || "");
  editor.innerHTML = availabilityDays.map((day) => {
    const selected = selectedByDay?.[day] || fallbackSlots;
    return `
      <div class="availability-day">
        <strong>${escapeHtml(day)}</strong>
        <div class="availability-slots">
          ${availabilitySlots.map((slot) => {
            const id = `availability-${day}-${slot}`.replace(/[^a-z0-9]/gi, "-");
            const checked = selected.includes(slot) ? "checked" : "";
            return `
              <label for="${id}" class="availability-toggle">
                <input id="${id}" type="checkbox" data-day="${escapeHtml(day)}" data-slot="${escapeHtml(slot)}" ${checked} />
                <span>${escapeHtml(slot)}</span>
              </label>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }).join("");
}

function selectedAvailabilityPayload() {
  const entries = [];
  document.querySelectorAll("#availabilityEditor input[type='checkbox']").forEach((input) => {
    entries.push({
      day_of_week: input.dataset.day,
      slot_time: input.dataset.slot,
      is_available: input.checked,
    });
  });
  return { availability: entries };
}

async function loadDoctorAvailability(id) {
  const data = await getJson(`/admin/doctors/${id}/availability`);
  const selectedByDay = {};
  availabilityDays.forEach((day) => {
    selectedByDay[day] = (data.availability?.[day] || [])
      .filter((slot) => slot.is_available)
      .map((slot) => slot.time);
  });
  renderAvailabilityEditor(selectedByDay);
}

async function saveDoctorAvailability(id) {
  const response = await apiFetch(`/admin/doctors/${id}/availability`, {
    method: "PUT",
    body: JSON.stringify(selectedAvailabilityPayload()),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not save doctor availability");
  }
}

async function fetchPendingDoctors() {
  const list = document.getElementById("pendingDoctors");
  const empty = document.getElementById("adminEmpty");
  if (!list || !empty) return;

  list.innerHTML = '<div class="loading" style="display:block;"><div class="spinner"></div><p>Loading pending doctors...</p></div>';
  empty.style.display = "none";

  try {
    const doctors = await getJson("/admin/doctors?status=pending");
    if (doctors.length === 0) {
      list.innerHTML = "";
      empty.style.display = "block";
      return;
    }

    empty.style.display = "none";
    list.innerHTML = doctors.map((doctor) => renderAdminDoctorCard(doctor, true)).join("");
    observeRevealElements(list);
  } catch (error) {
    list.innerHTML = `
      <div class="no-results">
        <span class="empty-icon">${svgIcon("shield")}</span>
        <h3>Could not load pending doctors</h3>
        <p>Please check that the backend is running at ${API_ORIGIN}.</p>
      </div>
    `;
  }
}

async function fetchAllDoctors() {
  const list = document.getElementById("allDoctors");
  if (!list) return;

  list.innerHTML = '<div class="loading" style="display:block;"><div class="spinner"></div><p>Loading doctor profiles...</p></div>';

  try {
    adminDoctors = await getJson("/admin/doctors");
    if (adminDoctors.length === 0) {
      list.innerHTML = `
        <div class="no-results">
          <span class="empty-icon">${svgIcon("stethoscope")}</span>
          <h3>No doctors yet</h3>
          <p>Use the form to add the first approved profile.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = adminDoctors.map((doctor) => renderAdminDoctorCard(doctor, false)).join("");
    observeRevealElements(list);
  } catch (error) {
    list.innerHTML = `
      <div class="no-results">
        <span class="empty-icon">${svgIcon("shield")}</span>
        <h3>Could not load doctor profiles</h3>
        <p>Please check that the backend is running at ${API_ORIGIN}.</p>
      </div>
    `;
  }
}

async function refreshAdminDoctors() {
  await Promise.all([fetchPendingDoctors(), fetchAllDoctors()]);
}

function renderAdminDoctorCard(doctor, showApprovalActions) {
  return `
    <article class="admin-doctor-card reveal">
      <header>
        <div class="doctor-card-identity">
          <div class="doctor-photo">${renderDoctorIcon()}</div>
          <div>
            <h3>${escapeHtml(doctor.name)}</h3>
            <span class="doctor-specialty-badge">${escapeHtml(doctor.specialty)}</span>
          </div>
        </div>
        <span class="status-badge status-${statusClass(doctor.approval_status)}">${escapeHtml(formatStatusLabel(doctor.approval_status))}</span>
      </header>
      <div class="admin-meta">
        <span>${svgIcon("stethoscope")} ${escapeHtml(doctor.hospital)}</span>
        <span>${svgIcon("map")} ${escapeHtml(doctor.location)}</span>
        <span>${svgIcon("phone")} ${escapeHtml(doctor.phone)}</span>
        <span>${svgIcon("calendar")} ${escapeHtml(doctorExperienceLabel(doctor))}</span>
        <span>${svgIcon("shield")} ${escapeHtml(doctor.qualification || "No qualification supplied")}</span>
        <span>${svgIcon("check")} ${escapeHtml(formatFee(doctor.fee))}</span>
      </div>
      <div class="admin-actions">
        <button type="button" class="btn btn-secondary" onclick="editDoctor(${doctor.id})">Edit</button>
        ${showApprovalActions ? `
          <button type="button" class="btn btn-approve" onclick="approveDoctor(${doctor.id})">Approve</button>
          <button type="button" class="btn btn-danger" onclick="rejectDoctor(${doctor.id})">Reject</button>
        ` : ""}
      </div>
    </article>
  `;
}

async function approveDoctor(id) {
  try {
    await getJson(`/admin/doctors/${id}/approve`, { method: "POST" });
    showAdminAlert("Doctor approved and published.");
    await refreshAdminDoctors();
  } catch (error) {
    showAdminAlert(error.message || "Approval failed.", "error");
  }
}

async function rejectDoctor(id) {
  try {
    await getJson(`/admin/doctors/${id}/reject`, { method: "POST" });
    showAdminAlert("Doctor registration rejected.");
    await refreshAdminDoctors();
  } catch (error) {
    showAdminAlert(error.message || "Rejection failed.", "error");
  }
}

function buildManualDoctorPayload() {
  return {
    name: document.getElementById("doctorName").value.trim(),
    specialty: document.getElementById("doctorSpecialty").value.trim(),
    hospital: document.getElementById("doctorHospital").value.trim(),
    location: document.getElementById("doctorLocation").value.trim(),
    phone: document.getElementById("doctorPhone").value.trim(),
    fee: document.getElementById("doctorFee").value,
    rating: document.getElementById("doctorRating").value,
    qualification: document.getElementById("doctorQualification").value.trim(),
    experience_years: document.getElementById("doctorExperience").value,
    approval_status: document.getElementById("doctorStatus").value,
  };
}

function fillDoctorForm(doctor) {
  document.getElementById("doctorName").value = doctor.name || "";
  document.getElementById("doctorSpecialty").value = doctor.specialty || "";
  document.getElementById("doctorHospital").value = doctor.hospital || "";
  document.getElementById("doctorLocation").value = doctor.location || "";
  document.getElementById("doctorPhone").value = doctor.phone || "";
  document.getElementById("doctorFee").value = doctor.fee ?? "";
  document.getElementById("doctorRating").value = doctor.rating ?? "4.8";
  document.getElementById("doctorExperience").value = doctor.experience_years ?? "0";
  document.getElementById("doctorQualification").value = doctor.qualification || "";
  document.getElementById("doctorStatus").value = doctor.approval_status || "approved";
}

function resetDoctorForm() {
  const form = document.getElementById("manualDoctorForm");
  const submitButton = document.getElementById("doctorSubmitButton");
  const cancelButton = document.getElementById("cancelDoctorEdit");
  editingDoctorId = null;
  form?.reset();
  document.getElementById("doctorRating").value = "4.8";
  document.getElementById("doctorExperience").value = "5";
  document.getElementById("doctorStatus").value = "approved";
  renderAvailabilityEditor();
  if (submitButton) submitButton.textContent = "Add approved doctor";
  if (cancelButton) cancelButton.style.display = "none";
}

async function editDoctor(id) {
  const doctor = adminDoctors.find((item) => Number(item.id) === Number(id));
  if (!doctor) {
    showAdminAlert("Could not find that doctor in the loaded list.", "error");
    return;
  }

  editingDoctorId = doctor.id;
  fillDoctorForm(doctor);
  try {
    await loadDoctorAvailability(doctor.id);
  } catch (error) {
    renderAvailabilityEditor();
    showAdminAlert(error.message || "Could not load doctor availability.", "error");
  }

  const submitButton = document.getElementById("doctorSubmitButton");
  const cancelButton = document.getElementById("cancelDoctorEdit");
  if (submitButton) submitButton.textContent = "Save changes";
  if (cancelButton) cancelButton.style.display = "inline-flex";
  document.getElementById("manualDoctorForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function saveDoctor(event) {
  event.preventDefault();
  const form = document.getElementById("manualDoctorForm");
  const wasEditing = Boolean(editingDoctorId);
  const endpoint = editingDoctorId ? `/admin/doctors/${editingDoctorId}` : "/doctors";
  const method = editingDoctorId ? "PUT" : "POST";

  try {
    const response = await apiFetch(endpoint, {
      method,
      body: JSON.stringify(buildManualDoctorPayload()),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not save doctor");
    }

    const savedDoctorId = editingDoctorId || data.id || data.doctor?.id;
    if (savedDoctorId) {
      await saveDoctorAvailability(savedDoctorId);
    }

    form.reset();
    resetDoctorForm();
    showAdminAlert(wasEditing ? "Doctor profile and availability updated." : "Doctor added with availability.");
    await refreshAdminDoctors();
  } catch (error) {
    showAdminAlert(error.message || "Could not save doctor.", "error");
  }
}

function statusClass(value) {
  return String(value || "pending")
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-");
}

function formatStatusLabel(value) {
  return String(value || "pending")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

document.addEventListener("DOMContentLoaded", () => {
  renderAvailabilityEditor();
  refreshAdminDoctors();

  const form = document.getElementById("manualDoctorForm");
  form?.addEventListener("submit", saveDoctor);
  document.getElementById("cancelDoctorEdit")?.addEventListener("click", resetDoctorForm);
  document.getElementById("doctorSpecialty")?.addEventListener("input", () => {
    if (!editingDoctorId) renderAvailabilityEditor();
  });
});
