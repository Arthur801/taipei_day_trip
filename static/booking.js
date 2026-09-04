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
  const signupDialog = document.querySelector(".dialog-signup");

  if (!bookingButton || !signinDialog) return;

  let isCheckingUser = false;

  function clearDialogMessage(dialog) {
    const message = dialog.querySelector(".dialog-message");
    if (!message) return;

    message.textContent = "";
    message.hidden = true;
    message.classList.remove("is-success");
  }

  function openSigninDialog() {
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
      const response = await fetch("/api/user/auth", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 403) {
        removeStoredToken();
        openSigninDialog();
        return;
      }

      if (!response.ok) {
        throw new Error(`Unable to check user status: ${response.status}`);
      }

      const { data } = await response.json();
      if (data) {
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

document.addEventListener("DOMContentLoaded", () => {
  initializeBookingNavigation();
  guardBookingPage();
});
