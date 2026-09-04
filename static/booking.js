function getStoredToken() {
  try {
    return localStorage.getItem("token");
  } catch (error) {
    console.error("Unable to read authentication token.", error);
    return null;
  }
}

function removeStoredToken() {
  try {
    localStorage.removeItem("token");
  } catch (error) {
    console.error("Unable to remove authentication token.", error);
  }
}

function clearDialogMessage(dialog) {
  const message = dialog.querySelector(".dialog-message");
  if (!message) return;

  message.textContent = "";
  message.hidden = true;
  message.classList.remove("is-success");
}

function openSigninDialog() {
  const signinDialog = document.querySelector(".dialog-signin");
  const signupDialog = document.querySelector(".dialog-signup");
  if (!signinDialog) return;

  if (signupDialog) {
    signupDialog.classList.remove("is-open");
    signupDialog.setAttribute("aria-hidden", "true");
  }

  clearDialogMessage(signinDialog);
  signinDialog.classList.add("is-open");
  signinDialog.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  signinDialog.querySelector("input")?.focus();
}

async function getSignedInUser(token) {
  const response = await fetch("/api/user/auth", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 403) return null;
  if (!response.ok) {
    throw new Error(`Unable to check user status: ${response.status}`);
  }

  const { data } = await response.json();
  return data;
}

async function guardBookingPage() {
  if (!document.body.classList.contains("booking-page-body")) return;

  const token = getStoredToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  try {
    const response = await fetch("/api/booking", { headers });

    if (response.status === 403) {
      removeStoredToken();
      window.location.replace("/");
      return;
    }

    if (!response.ok) {
      throw new Error(`Unable to load booking: ${response.status}`);
    }
  } catch (error) {
    console.error("Unable to verify booking page access.", error);
  }
}

function initializeBookingNavigation() {
  const bookingButton = document.querySelector("#booking-nav-button");
  const signinDialog = document.querySelector(".dialog-signin");

  if (!bookingButton || !signinDialog) return;

  let isCheckingUser = false;

  bookingButton.addEventListener("click", async () => {
    if (isCheckingUser) return;

    const token = getStoredToken();
    if (!token) {
      openSigninDialog();
      return;
    }

    isCheckingUser = true;
    bookingButton.disabled = true;

    try {
      const user = await getSignedInUser(token);
      if (user) {
        window.location.assign("/booking");
        return;
      }

      removeStoredToken();
      openSigninDialog();
    } catch (error) {
      console.error("Unable to open booking page.", error);
      openSigninDialog();
    } finally {
      isCheckingUser = false;
      bookingButton.disabled = false;
    }
  });
}

function getBookingAttractionId() {
  const match = window.location.pathname.match(/^\/attraction\/([1-9]\d*)\/?$/);
  return match ? Number(match[1]) : null;
}

function initializeAttractionBooking() {
  const submitButton = document.querySelector("#booking-button");
  const dateInput = document.querySelector("#booking-date");
  if (!submitButton || !dateInput) return;

  let isCreatingBooking = false;

  dateInput.addEventListener("input", () => dateInput.setCustomValidity(""));

  submitButton.addEventListener("click", async () => {
    if (isCreatingBooking) return;

    const token = getStoredToken();
    if (!token) {
      openSigninDialog();
      return;
    }

    isCreatingBooking = true;
    submitButton.disabled = true;

    try {
      const user = await getSignedInUser(token);
      if (!user) {
        removeStoredToken();
        openSigninDialog();
        return;
      }

      if (!dateInput.value) {
        dateInput.setCustomValidity("請選擇日期");
        dateInput.reportValidity();
        return;
      }

      const attractionId = getBookingAttractionId();
      const selectedTime = document.querySelector('input[name="booking-time"]:checked');
      if (!attractionId || !selectedTime) {
        throw new Error("Unable to read booking details from the attraction page.");
      }

      const time = selectedTime.value;
      const price = time === "afternoon" ? 2500 : 2000;
      const response = await fetch("/api/booking", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          attractionId,
          date: dateInput.value,
          time,
          price,
        }),
      });

      if (response.status === 403) {
        removeStoredToken();
        openSigninDialog();
        return;
      }

      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) {
        throw new Error(data.message || `Unable to create booking: ${response.status}`);
      }

      window.location.assign("/booking");
    } catch (error) {
      console.error("Unable to create booking.", error);
      window.alert("預定行程失敗，請稍後再試");
    } finally {
      isCreatingBooking = false;
      submitButton.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initializeBookingNavigation();
  initializeAttractionBooking();
  guardBookingPage();
});
