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
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch("/api/user/auth", {
    headers,
  });

  if (response.status === 403) return null;
  if (!response.ok) {
    throw new Error(`Unable to check user status: ${response.status}`);
  }

  const { data } = await response.json();
  return data;
}

function renderBookingUser(user) {
  const memberName = document.querySelector("#booking-member-name");
  const contactName = document.querySelector("#contact-name");
  const contactEmail = document.querySelector("#contact-email");

  if (memberName) memberName.textContent = user.name;
  if (contactName) contactName.value = user.name;
  if (contactEmail) contactEmail.value = user.email;
}

function renderEmptyBooking() {
  const emptyMessage = document.querySelector("#booking-empty");
  const bookingContent = document.querySelector("#booking-content");

  document.body.classList.remove("has-booking");
  if (emptyMessage) {
    emptyMessage.textContent = "目前沒有任何待預訂的行程";
    emptyMessage.hidden = false;
  }
  if (bookingContent) bookingContent.hidden = true;
}

function getBookingImageUrl(imagePath) {
  if (!imagePath) return "";
  if (imagePath.startsWith("http")) return imagePath;
  return `https://padax.github.io/taipei-day-trip-resources${imagePath}`;
}

function renderBooking(booking) {
  const emptyMessage = document.querySelector("#booking-empty");
  const bookingContent = document.querySelector("#booking-content");
  const image = document.querySelector("#booking-attraction-image");
  const attractionName = document.querySelector("#booking-attraction-name");
  const date = document.querySelector("#booking-date-display");
  const time = document.querySelector("#booking-time-display");
  const price = document.querySelector("#booking-price-display");
  const address = document.querySelector("#booking-address");
  const totalPrice = document.querySelector("#booking-total-price");
  const attraction = booking.attraction;

  if (!bookingContent || !attraction) {
    throw new Error("Booking API returned incomplete data.");
  }

  document.body.classList.add("has-booking");
  if (emptyMessage) emptyMessage.hidden = true;
  bookingContent.hidden = false;

  if (image) {
    const imageUrl = getBookingImageUrl(attraction.image);
    if (imageUrl) image.src = imageUrl;
    else image.removeAttribute("src");
    image.alt = attraction.name || "預定景點";
  }
  if (attractionName) attractionName.textContent = attraction.name || "";
  if (date) date.textContent = booking.date || "";
  if (time) {
    time.textContent = booking.time === "afternoon"
      ? "下午 2 點到晚上 9 點"
      : "早上 9 點到下午 4 點";
  }
  if (price) price.textContent = booking.price;
  if (address) address.textContent = attraction.address || "";
  if (totalPrice) totalPrice.textContent = booking.price;
}

function initializeDeleteBooking(token) {
  const deleteButton = document.querySelector("#booking-delete");
  if (!deleteButton) return;

  deleteButton.addEventListener("click", async () => {
    if (deleteButton.disabled) return;
    deleteButton.disabled = true;

    try {
      const response = await fetch("/api/booking", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 403) {
        removeStoredToken();
        window.location.replace("/");
        return;
      }

      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) {
        throw new Error(data.message || `Unable to delete booking: ${response.status}`);
      }

      window.location.reload();
    } catch (error) {
      console.error("Unable to delete booking.", error);
      window.alert("刪除預定行程失敗，請稍後再試");
      deleteButton.disabled = false;
    }
  });
}

async function initializeBookingPage() {
  if (!document.body.classList.contains("booking-page-body")) return;

  const token = getStoredToken();

  try {
    const user = await getSignedInUser(token);
    if (!user) {
      removeStoredToken();
      window.location.replace("/");
      return;
    }

    renderBookingUser(user);

    const response = await fetch("/api/booking", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 403) {
      removeStoredToken();
      window.location.replace("/");
      return;
    }

    if (!response.ok) {
      throw new Error(`Unable to load booking: ${response.status}`);
    }

    const { data } = await response.json();
    if (data === null) {
      renderEmptyBooking();
      return;
    }

    renderBooking(data);
    initializeDeleteBooking(token);
  } catch (error) {
    console.error("Unable to initialize booking page.", error);
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
  initializeBookingPage();
});
