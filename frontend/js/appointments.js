// Appointments page JavaScript

// Fetch user's appointments
async function fetchAppointments() {
  showLoading();

  const userId = getUserId();

  try {
    const response = await fetch(
      `${API_BASE_URL}/appointments?user_id=${userId}`,
    );
    if (!response.ok) throw new Error("Failed to fetch appointments");

    const appointments = await response.json();
    displayAppointments(appointments);
  } catch (error) {
    console.error("Error fetching appointments:", error);
    document.getElementById("appointmentsList").innerHTML = `
            <div class="no-results">
                <span style="font-size: 48px;">⚠️</span>
                <p>Failed to load appointments. Please try again later.</p>
            </div>
        `;
  } finally {
    hideLoading();
  }
}

// Display appointments
function displayAppointments(appointments) {
  const appointmentsList = document.getElementById("appointmentsList");
  const noAppointments = document.getElementById("noAppointments");

  if (appointments.length === 0) {
    appointmentsList.innerHTML = "";
    noAppointments.style.display = "block";
    return;
  }

  noAppointments.style.display = "none";

  appointmentsList.innerHTML = appointments
    .map(
      (appointment) => `
        <div class="appointment-card">
            <div class="appointment-icon">📅</div>
            <div class="appointment-info">
                <h3>Appointment with ${appointment.doctor_name}</h3>
                <p class="specialty">${appointment.doctor_specialty}</p>
                <div class="appointment-meta">
                    <div class="meta-item">
                        <span>📅</span>
                        <span>${formatDate(appointment.appointment_date)}</span>
                    </div>
                    <div class="meta-item">
                        <span>🕐</span>
                        <span>${appointment.appointment_time}</span>
                    </div>
                    <div class="meta-item">
                        <span>📝</span>
                        <span>${appointment.reason}</span>
                    </div>
                </div>
                <div style="margin-top: 0.5rem; color: #6b7280; font-size: 0.85rem;">
                    Booked on: ${appointment.created_at}
                </div>
            </div>
            <div class="status-badge status-${appointment.status}">
                ${appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
            </div>
        </div>
    `,
    )
    .join("");
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  fetchAppointments();
});
