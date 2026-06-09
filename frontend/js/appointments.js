async function fetchAppointments() {
  showLoading();

  try {
    const auth = await getJson("/me");
    if (!auth.authenticated) {
      renderLoginRequired();
      return;
    }

    const appointments = await getJson("/appointments");
    displayAppointments(appointments);
  } catch (error) {
    console.error("Error fetching appointments:", error);
    const list = document.getElementById("appointmentsList");
    if (list) {
      list.innerHTML = `
        <div class="no-results">
          <span class="empty-icon">${svgIcon("shield")}</span>
          <h2>Could not load appointments</h2>
          <p>Please check that the backend is running at ${API_ORIGIN}.</p>
        </div>
      `;
    }
  } finally {
    hideLoading();
  }
}

function renderLoginRequired() {
  const intro = document.getElementById("appointmentsIntro");
  const list = document.getElementById("appointmentsList");
  const empty = document.getElementById("noAppointments");
  updateAppointmentMetrics([]);

  if (intro) intro.textContent = "Please log in as a patient to view appointments.";
  if (empty) empty.style.display = "none";
  if (list) {
    list.innerHTML = `
      <div class="no-results">
        <span class="empty-icon">${svgIcon("calendar")}</span>
        <h2>Login required</h2>
        <p>Your appointment dashboard is available after login.</p>
        <div class="login-required-actions" style="justify-content:center;margin-top:16px;">
          <a href="login.html" class="btn btn-primary">Login</a>
          <a href="register.html" class="btn btn-secondary">Register</a>
        </div>
      </div>
    `;
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

function renderPaymentReturnNotice() {
  const params = new URLSearchParams(window.location.search);
  const payment = params.get("payment");
  const dashboard = document.querySelector(".appointments-dashboard");
  if (!payment || !dashboard) return;

  const messages = {
    success: {
      title: "Payment successful",
      body: "Your appointment has been confirmed.",
    },
    failed: {
      title: "Payment was not completed",
      body: "Your appointment is still saved, but payment failed. You can book again or contact support.",
    },
    cancelled: {
      title: "Payment cancelled",
      body: "Your appointment is still saved as payment pending, and no sandbox payment was taken.",
    },
    error: {
      title: "Payment status unavailable",
      body: params.get("message") || "We could not match the payment response to an appointment.",
    },
  };

  const notice = messages[payment] || messages.error;
  const noticeElement = document.createElement("div");
  noticeElement.className = `payment-notice payment-notice-${statusClass(payment)}`;
  noticeElement.innerHTML = `
    <strong>${escapeHtml(notice.title)}</strong>
    <span>${escapeHtml(notice.body)}</span>
  `;
  dashboard.prepend(noticeElement);
}

function updateAppointmentMetrics(appointments) {
  const total = document.getElementById("appointmentTotal");
  const upcoming = document.getElementById("appointmentUpcoming");
  const latest = document.getElementById("appointmentLatest");
  const upcomingCount = appointments.filter(isUpcomingAppointment).length;
  const latestAppointment = [...appointments].sort((a, b) => {
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  })[0];

  if (total) total.textContent = String(appointments.length);
  if (upcoming) upcoming.textContent = String(upcomingCount);
  if (latest) {
    const latestDate = latestAppointment?.created_at?.split("T")[0] || latestAppointment?.appointment_date;
    latest.textContent = latestDate ? formatDate(latestDate) : "--";
  }
}

function appointmentDateTime(appointment) {
  const timeValue = appointment.appointment_time || "00:00";
  const normalizedTime = /am|pm/i.test(timeValue) ? timeValue : timeValue.slice(0, 5);
  const parsed = new Date(`${appointment.appointment_date} ${normalizedTime}`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isPastAppointment(appointment) {
  if (typeof appointment.is_past === "boolean") return appointment.is_past;
  const parsed = appointmentDateTime(appointment);
  return parsed ? parsed < new Date() : false;
}

function isUpcomingAppointment(appointment) {
  if (typeof appointment.is_upcoming === "boolean") return appointment.is_upcoming;
  const paymentStatus = String(appointment.payment_status || "").toLowerCase();
  const parsed = appointmentDateTime(appointment);
  return Boolean(parsed && parsed >= new Date() && ["paid", "confirmed"].includes(paymentStatus));
}

function isPendingPaymentAppointment(appointment) {
  if (typeof appointment.is_pending_payment === "boolean") return appointment.is_pending_payment;
  const paymentStatus = String(appointment.payment_status || "pending").toLowerCase();
  return ["pending", "failed"].includes(paymentStatus) && !isPastAppointment(appointment);
}

function groupAppointments(appointments) {
  const upcoming = [];
  const pending = [];
  const past = [];

  appointments.forEach((appointment) => {
    if (isPendingPaymentAppointment(appointment)) {
      pending.push(appointment);
    } else if (isUpcomingAppointment(appointment)) {
      upcoming.push(appointment);
    } else {
      past.push(appointment);
    }
  });

  upcoming.sort((a, b) => `${a.appointment_date} ${a.appointment_time}`.localeCompare(`${b.appointment_date} ${b.appointment_time}`));
  pending.sort((a, b) => `${a.appointment_date} ${a.appointment_time}`.localeCompare(`${b.appointment_date} ${b.appointment_time}`));
  past.sort((a, b) => `${b.appointment_date} ${b.appointment_time}`.localeCompare(`${a.appointment_date} ${a.appointment_time}`));

  return { upcoming, pending, past };
}

function paymentBadgeLabel(paymentStatus) {
  const normalized = String(paymentStatus || "pending").toLowerCase();
  if (normalized === "paid" || normalized === "confirmed") return "Payment Paid";
  if (normalized === "cancelled") return "Payment Cancelled";
  return "Payment Pending";
}

function renderAppointmentActions(appointment) {
  if (!isPendingPaymentAppointment(appointment)) return "";

  return `
    <div class="appointment-actions">
      <button type="button" class="btn btn-primary" onclick="retryAppointmentPayment(${appointment.id})">Retry Payment</button>
      <button type="button" class="btn btn-danger" onclick="cancelPendingAppointment(${appointment.id})">Cancel Booking</button>
    </div>
  `;
}

function renderAppointmentCard(appointment) {
  const status = appointment.display_status || appointment.status || "scheduled";
  const paymentStatus = appointment.payment_status || "pending";
  const transactionInfo = paymentStatus === "paid" && appointment.transaction_id
    ? `
        <p class="transaction-line">
          Transaction ID: <strong>${escapeHtml(appointment.transaction_id)}</strong>
          ${appointment.payment_method ? `<span>${escapeHtml(appointment.payment_method)}</span>` : ""}
        </p>
      `
    : "";

  return `
    <article class="appointment-card reveal">
      <div class="doctor-photo">${renderDoctorIcon()}</div>
      <div>
        <h3>${escapeHtml(appointment.doctor_name || "Doctor")}</h3>
        <p class="specialty">${escapeHtml(appointment.doctor_specialty || "Specialist")}</p>
        <div class="appointment-meta">
          <span class="appointment-meta-item">${svgIcon("calendar")} ${formatDate(appointment.appointment_date)}</span>
          <span class="appointment-meta-item">${svgIcon("clock")} ${escapeHtml(appointment.appointment_time)}</span>
          <span class="appointment-meta-item">${svgIcon("shield")} ${escapeHtml(appointment.reason)}</span>
        </div>
        <p style="margin:12px 0 0;color:var(--muted);font-size:0.88rem;">
          Booked ${escapeHtml(formatDateTime(appointment.created_at))}
        </p>
        ${transactionInfo}
        ${renderAppointmentActions(appointment)}
      </div>
      <div class="appointment-badges">
        <span class="status-badge status-${statusClass(status)}">${escapeHtml(formatStatusLabel(status))}</span>
        <span class="status-badge payment-badge payment-${statusClass(paymentStatus)}">${escapeHtml(paymentBadgeLabel(paymentStatus))}</span>
      </div>
    </article>
  `;
}

function renderAppointmentSection(title, appointments, emptyText) {
  return `
    <section class="appointment-group">
      <div class="appointment-group-header">
        <h3>${escapeHtml(title)}</h3>
        <span>${appointments.length}</span>
      </div>
      ${appointments.length > 0 ? appointments.map(renderAppointmentCard).join("") : `<p class="appointment-group-empty">${escapeHtml(emptyText)}</p>`}
    </section>
  `;
}

function displayAppointments(appointments) {
  const appointmentsList = document.getElementById("appointmentsList");
  const noAppointments = document.getElementById("noAppointments");
  const intro = document.getElementById("appointmentsIntro");

  if (!appointmentsList || !noAppointments) return;
  updateAppointmentMetrics(appointments);

  if (appointments.length === 0) {
    appointmentsList.innerHTML = "";
    noAppointments.style.display = "block";
    if (intro) intro.textContent = "No appointment history yet.";
    return;
  }

  noAppointments.style.display = "none";
  if (intro) intro.textContent = `${appointments.length} appointment${appointments.length === 1 ? "" : "s"} found.`;

  const grouped = groupAppointments(appointments);
  appointmentsList.innerHTML = [
    renderAppointmentSection("Upcoming Appointments", grouped.upcoming, "No confirmed upcoming appointments."),
    renderAppointmentSection("Pending Payment", grouped.pending, "No appointments are waiting for payment."),
    renderAppointmentSection("Past Appointments", grouped.past, "No past appointment history yet."),
  ].join("");

  observeRevealElements(appointmentsList);
}

async function retryAppointmentPayment(id) {
  try {
    const response = await apiFetch("/payments/initiate", {
      method: "POST",
      body: JSON.stringify({ appointment_id: id }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not restart payment");
    }

    const paymentUrl = data.payment_url || data.gateway_page_url;
    if (!paymentUrl) {
      throw new Error("Payment gateway URL was not returned.");
    }

    window.location.href = paymentUrl;
  } catch (error) {
    alert(error.message || "Could not restart payment. Please try again.");
  }
}

async function cancelPendingAppointment(id) {
  if (!window.confirm("Cancel this unpaid booking?")) return;

  try {
    const response = await apiFetch(`/appointments/${id}/cancel`, { method: "POST" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not cancel booking");
    }

    await fetchAppointments();
  } catch (error) {
    alert(error.message || "Could not cancel booking. Please try again.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderPaymentReturnNotice();
  fetchAppointments();
});
