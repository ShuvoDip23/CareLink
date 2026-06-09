let allDoctors = [];
let allSpecialties = [];

async function fetchDoctors() {
  showLoading();

  try {
    allDoctors = await getJson("/doctors");
    await fetchSpecialties();
    applyUrlSpecialty();
    filterDoctors();
  } catch (error) {
    console.error("Error fetching doctors:", error);
    const doctorsList = document.getElementById("doctorsList");
    if (doctorsList) {
      doctorsList.innerHTML = `
        <div class="no-results-card">
          <span class="empty-icon">${svgIcon("shield")}</span>
          <h3>Failed to load doctors</h3>
          <p>Please check that the backend is running at ${API_ORIGIN}.</p>
        </div>
      `;
    }
  } finally {
    hideLoading();
  }
}

async function fetchSpecialties() {
  try {
    allSpecialties = await getJson("/specialties");
    populateSpecialtyFilter();
  } catch (error) {
    console.error("Error fetching specialties:", error);
  }
}

function populateSpecialtyFilter() {
  const filter = document.getElementById("specialtyFilter");
  if (!filter) return;

  filter.innerHTML = '<option value="">All specialties</option>';
  [...allSpecialties].sort().forEach((specialty) => {
    const option = document.createElement("option");
    option.value = specialty;
    option.textContent = specialty;
    filter.appendChild(option);
  });
}

function applyUrlSpecialty() {
  const specialty = new URLSearchParams(window.location.search).get("specialty");
  const specialtyFilter = document.getElementById("specialtyFilter");
  if (specialty && specialtyFilter) {
    specialtyFilter.value = specialty;
  }
}

function formatExperienceLabel(experienceYears) {
  const years = Number(experienceYears || 0);
  return years > 0 ? `${years} years experience` : "Experience not updated";
}

function displayDoctors(doctors) {
  const doctorsList = document.getElementById("doctorsList");
  const noResults = document.getElementById("noResults");
  if (!doctorsList || !noResults) return;

  if (doctors.length === 0) {
    doctorsList.innerHTML = "";
    noResults.style.display = "block";
    return;
  }

  noResults.style.display = "none";
  doctorsList.innerHTML = doctors
    .map((doctor) => {
      const rating = Number(doctor.rating || 0).toFixed(1);
      return `
        <a href="doctor.html?id=${doctor.id}" class="doctor-card-new reveal">
          <div class="doctor-card-top">
            <div class="doctor-card-identity">
              <div class="doctor-photo">${renderDoctorIcon()}</div>
              <div class="doctor-top-info">
                <h3>${escapeHtml(doctor.name)}</h3>
                <span class="doctor-specialty-badge">${escapeHtml(doctor.specialty)}</span>
              </div>
            </div>
            <span class="availability-badge">Available</span>
          </div>

          <div class="doctor-meta-list">
            <div class="doctor-meta-item">
              ${svgIcon("stethoscope")}
              <span>${escapeHtml(doctor.hospital)}</span>
            </div>
            <div class="doctor-meta-item">
              ${svgIcon("map")}
              <span>${escapeHtml(doctor.location)}</span>
            </div>
            <div class="doctor-meta-item">
              ${svgIcon("calendar")}
              <span>${escapeHtml(formatExperienceLabel(doctor.experience_years))}</span>
            </div>
          </div>

          <div class="doctor-card-bottom">
            <span class="doctor-rating-row">
              <span class="stars">${renderStars(rating)}</span>
              <span>${escapeHtml(rating)}</span>
            </span>
            <span class="doctor-fee-pill">${escapeHtml(formatFee(doctor.fee))}</span>
          </div>

          <div class="doctor-card-cta">
            <span>View Profile</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
          </div>
        </a>
      `;
    })
    .join("");

  observeRevealElements(doctorsList);
}

function filterDoctors() {
  const specialty = document.getElementById("specialtyFilter")?.value || "";
  const searchQuery = (document.getElementById("searchInput")?.value || "").toLowerCase().trim();

  let filtered = [...allDoctors];

  if (specialty) {
    filtered = filtered.filter((doctor) => doctor.specialty === specialty);
  }

  if (searchQuery) {
    filtered = filtered.filter((doctor) => {
      const haystack = `${doctor.name} ${doctor.specialty} ${doctor.hospital} ${doctor.location}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  }

  displayDoctors(filtered);
}

document.addEventListener("DOMContentLoaded", fetchDoctors);
