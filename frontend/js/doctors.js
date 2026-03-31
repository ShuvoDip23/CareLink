// Doctors page JavaScript
let allDoctors = [];
let allSpecialties = [];

// Fetch doctors and populate the page
async function fetchDoctors() {
  showLoading();

  try {
    const response = await fetch(`${API_BASE_URL}/doctors`);
    if (!response.ok) throw new Error("Failed to fetch doctors");

    allDoctors = await response.json();
    displayDoctors(allDoctors);

    // Fetch specialties for filter
    await fetchSpecialties();

    // Check if there's a specialty filter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const specialty = urlParams.get("specialty");
    if (specialty) {
      document.getElementById("specialtyFilter").value = specialty;
      filterDoctors();
    }
  } catch (error) {
    console.error("Error fetching doctors:", error);
    document.getElementById("doctorsList").innerHTML = `
            <div class="no-results">
                <span style="font-size: 48px;">⚠️</span>
                <p>Failed to load doctors. Please try again later.</p>
            </div>
        `;
  } finally {
    hideLoading();
  }
}

// Fetch specialties for filter dropdown
async function fetchSpecialties() {
  try {
    const response = await fetch(`${API_BASE_URL}/specialties`);
    if (!response.ok) throw new Error("Failed to fetch specialties");

    allSpecialties = await response.json();
    populateSpecialtyFilter();
  } catch (error) {
    console.error("Error fetching specialties:", error);
  }
}

// Populate specialty filter dropdown
function populateSpecialtyFilter() {
  const filter = document.getElementById("specialtyFilter");
  allSpecialties.forEach((specialty) => {
    const option = document.createElement("option");
    option.value = specialty;
    option.textContent = specialty;
    filter.appendChild(option);
  });
}

// Display doctors in grid
function displayDoctors(doctors) {
  const doctorsList = document.getElementById("doctorsList");
  const noResults = document.getElementById("noResults");

  if (doctors.length === 0) {
    doctorsList.innerHTML = "";
    noResults.style.display = "block";
    return;
  }

  noResults.style.display = "none";

  doctorsList.innerHTML = doctors
    .map(
      (doctor) => `
        <a href="doctor.html?id=${doctor.id}" class="doctor-card">
            <div class="doctor-header">
                <div class="doctor-avatar">👨‍⚕️</div>
                <div class="doctor-title">
                    <h3>${doctor.name}</h3>
                    <p class="specialty">${doctor.specialty}</p>
                </div>
            </div>
            <div class="doctor-details">
                <div class="detail-row">
                    <span>🏥</span>
                    <span>${doctor.hospital}</span>
                </div>
                <div class="detail-row">
                    <span>📍</span>
                    <span>${doctor.location}</span>
                </div>
                <div class="detail-row">
                    <span>📞</span>
                    <span>${doctor.phone}</span>
                </div>
                <div class="detail-row">
                    <div class="rating">
                        
                        <span>${doctor.rating}</span>
                        <span>⭐</span>
                    </div>
                    <span class="fee">${doctor.fee}</span>
                </div>
            </div>
        </a>
    `,
    )
    .join("");
}

// Filter doctors based on specialty and search query
function filterDoctors() {
  const specialty = document.getElementById("specialtyFilter").value;
  const searchQuery = document
    .getElementById("searchInput")
    .value.toLowerCase();

  let filtered = allDoctors;

  if (specialty) {
    filtered = filtered.filter((doctor) => doctor.specialty === specialty);
  }

  if (searchQuery) {
    filtered = filtered.filter((doctor) =>
      doctor.name.toLowerCase().includes(searchQuery),
    );
  }

  displayDoctors(filtered);
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  fetchDoctors();
});
