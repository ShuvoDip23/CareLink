// Doctor detail page JavaScript
let currentDoctor = null;

// Get doctor ID from URL
function getDoctorIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("id");
}

// Fetch doctor details
async function fetchDoctorDetails() {
  const doctorId = getDoctorIdFromUrl();

  if (!doctorId) {
    window.location.href = "doctors.html";
    return;
  }

  showLoading();

  try {
    const response = await fetch(`${API_BASE_URL}/doctors/${doctorId}`);
    if (!response.ok) throw new Error("Failed to fetch doctor details");

    currentDoctor = await response.json();
    displayDoctorDetails(currentDoctor);
  } catch (error) {
    console.error("Error fetching doctor details:", error);
    document.getElementById("doctorDetail").innerHTML = `
            <div class="no-results">
                <span style="font-size: 48px;">⚠️</span>
                <p>Failed to load doctor details. Please try again later.</p>
                <a href="doctors.html" class="btn btn-primary">Back to Doctors</a>
            </div>
        `;
  } finally {
    hideLoading();
  }
}

// Display doctor details
function displayDoctorDetails(doctor) {
  document.getElementById("doctorName").textContent = doctor.name;
  document.getElementById("doctorSpecialty").textContent = doctor.specialty;
  document.getElementById("doctorRating").innerHTML = `⭐ ${doctor.rating}`;
  document.getElementById("doctorHospital").textContent = doctor.hospital;
  document.getElementById("doctorLocation").textContent = doctor.location;
  document.getElementById("doctorPhone").textContent = doctor.phone;
  document.getElementById("doctorFee").textContent = `$${doctor.fee}`;

  document.getElementById("doctorDetail").style.display = "grid";
}

// Book appointment
async function bookAppointment(event) {
  event.preventDefault();

  const patientName = document.getElementById("patientName").value;
  const appointmentDate = document.getElementById("appointmentDate").value;
  const appointmentTime = document.getElementById("appointmentTime").value;
  const reason = document.getElementById("reason").value;

  const appointmentData = {
    user_id: getUserId(),
    user_name: patientName,
    doctor_id: currentDoctor.id,
    appointment_date: appointmentDate,
    appointment_time: appointmentTime,
    reason: reason,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/appointments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(appointmentData),
    });

    if (!response.ok) throw new Error("Failed to book appointment");

    const result = await response.json();
    console.log("Appointment booked:", result);

    // Show success modal
    showModal();

    // Reset form
    document.getElementById("bookingForm").reset();
  } catch (error) {
    console.error("Error booking appointment:", error);
    alert("Failed to book appointment. Please try again.");
  }
}

// Show success modal
function showModal() {
  const modal = document.getElementById("successModal");
  modal.classList.add("active");
}

// Close modal
function closeModal() {
  const modal = document.getElementById("successModal");
  modal.classList.remove("active");
}

// Close modal when clicking outside
window.onclick = function (event) {
  const modal = document.getElementById("successModal");
  if (event.target === modal) {
    closeModal();
  }
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  fetchDoctorDetails();
  setMinDate();
});
