let currentDoctor = null;
let isDoctorPageAuthenticated = false;
let currentPatient = null;

function getDoctorIdFromUrl() {
  return new URLSearchParams(window.location.search).get("id");
}

function setBookingState(isAuthenticated, user = null) {
  isDoctorPageAuthenticated = isAuthenticated;
  currentPatient = user;

  const loggedOut = document.getElementById("bookingLoggedOut");
  const loggedIn = document.getElementById("bookingLoggedIn");
  if (loggedOut) loggedOut.style.display = isAuthenticated ? "none" : "grid";
  if (loggedIn) loggedIn.style.display = isAuthenticated ? "block" : "none";

  const patientName = document.getElementById("patientName");
  if (patientName && user?.name) {
    patientName.value = user.name;
  }
}

function setupTimeSlotButtons() {
  const timeInput = document.getElementById("appointmentTime");
  const slotGrid = document.getElementById("timeSlotGrid");
  if (!timeInput || !slotGrid) return;

  slotGrid.querySelectorAll(".time-slot").forEach((slot) => {
    slot.addEventListener("click", () => {
      slotGrid.querySelectorAll(".time-slot").forEach((item) => item.classList.remove("active"));
      slot.classList.add("active");
      timeInput.value = slot.dataset.time || "";
    });
  });
}

async function checkDoctorPageAuth() {
  try {
    const data = await getJson("/me");
    setBookingState(Boolean(data.authenticated), data.user || null);
  } catch (error) {
    setBookingState(false);
  }
}

async function fetchDoctorDetails() {
  const doctorId = getDoctorIdFromUrl();
  if (!doctorId) {
    window.location.href = "doctors.html";
    return;
  }

  showLoading();

  try {
    currentDoctor = await getJson(`/doctors/${doctorId}`);
    displayDoctorDetails(currentDoctor);
  } catch (error) {
    console.error("Error fetching doctor details:", error);
    const doctorDetail = document.getElementById("doctorDetail");
    if (doctorDetail) {
      doctorDetail.innerHTML = `
        <div class="no-results-card">
          <span class="empty-icon">${svgIcon("shield")}</span>
          <h3>Doctor profile unavailable</h3>
          <p>The doctor may be pending approval or the profile could not be loaded.</p>
          <a href="doctors.html" class="btn btn-primary" style="margin-top:16px;">Back to Doctors</a>
        </div>
      `;
      doctorDetail.style.display = "block";
    }
  } finally {
    hideLoading();
  }
}

function displayDoctorDetails(doctor) {
  document.getElementById("doctorAvatarLarge").innerHTML = renderDoctorIcon();
  document.getElementById("doctorName").textContent = doctor.name;
  document.getElementById("doctorSpecialty").textContent = doctor.specialty;
  const rating = Number(doctor.rating || 0).toFixed(1);
  document.getElementById("doctorRating").innerHTML = `
    <span class="stars">${renderStars(rating)}</span>
    <span>${escapeHtml(rating)} patient rating</span>
  `;
  document.getElementById("doctorHospital").textContent = doctor.hospital;
  document.getElementById("doctorLocation").textContent = doctor.location;
  document.getElementById("doctorPhone").textContent = doctor.phone;
  document.getElementById("doctorFee").textContent = formatFee(doctor.fee);
  document.getElementById("doctorQualification").textContent = doctor.qualification || "Not provided";
  const experienceYears = Number(doctor.experience_years || 0);
  document.getElementById("doctorExperience").textContent = experienceYears > 0 ? `${experienceYears} years experience` : "Experience not updated";
  const bookingFee = document.getElementById("bookingFee");
  if (bookingFee) bookingFee.textContent = formatFee(doctor.fee);

  document.getElementById("doctorDetail").style.display = "grid";
}

async function bookAppointment(event) {
  event.preventDefault();

  if (!isDoctorPageAuthenticated) {
    setBookingState(false);
    return;
  }

  const appointmentData = {
    user_name: document.getElementById("patientName").value.trim(),
    doctor_id: currentDoctor.id,
    appointment_date: document.getElementById("appointmentDate").value,
    appointment_time: document.getElementById("appointmentTime").value,
    reason: document.getElementById("reason").value.trim(),
  };

  if (!appointmentData.appointment_time) {
    alert("Please select an appointment time.");
    return;
  }

  const submitButton = document.getElementById("bookingSubmit");
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Opening SSLCommerz...";
  }

  try {
    const response = await apiFetch("/appointments", {
      method: "POST",
      body: JSON.stringify(appointmentData),
    });

    if (response.status === 401) {
      setBookingState(false);
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = "Proceed to Payment";
      }
      return;
    }

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to book appointment");
    }

    const paymentUrl = result.payment_url || result.gateway_page_url;
    if (!paymentUrl) {
      throw new Error("Appointment was created, but the payment gateway URL was not returned.");
    }

    window.location.href = paymentUrl;
  } catch (error) {
    console.error("Error booking appointment:", error);
    alert(error.message || "Failed to book appointment. Please try again.");
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = "Proceed to Payment";
    }
  }
}

function showModal() {
  document.getElementById("successModal")?.classList.add("active");
}

function closeModal() {
  document.getElementById("successModal")?.classList.remove("active");
}

window.onclick = function (event) {
  const modal = document.getElementById("successModal");
  if (event.target === modal) {
    closeModal();
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  setMinDate();
  setupTimeSlotButtons();
  await checkDoctorPageAuth();
  await fetchDoctorDetails();
  observeRevealElements();
});
