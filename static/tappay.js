const TAPPAY_CONFIG = Object.freeze({
  // Replace these values with the App ID and App Key from TapPay Portal.
  appId: 171130,
  appKey: "app_5xekHY6s1VZX5v7Bs6et8eIqkTbD9NIhZigEzjXpAfDnchpIu3JXbpvXgLZx",
  serverType: "sandbox",
});

const TAPPAY_FIELD_IDS = Object.freeze({
  number: "card-number",
  expiry: "card-expiration-date",
  ccv: "card-ccv",
});

function setTapPayMessage(message, type = "error") {
  const messageElement = document.querySelector("#tappay-message");
  if (!messageElement) return;

  messageElement.textContent = message;
  messageElement.hidden = !message;
  messageElement.classList.toggle("is-success", type === "success");
}

function setTapPayFieldState(fieldId, status, showIncompleteAsError = false) {
  const field = document.getElementById(fieldId);
  if (!field) return;

  const isValid = status === 0;
  const isError = status === 2 || (showIncompleteAsError && !isValid);
  field.classList.toggle("is-valid", isValid);
  field.classList.toggle("is-error", isError);
  field.setAttribute("aria-invalid", String(isError));
}

function updateTapPayFieldStates(status = {}, showIncompleteAsError = false) {
  setTapPayFieldState(TAPPAY_FIELD_IDS.number, status.number, showIncompleteAsError);
  setTapPayFieldState(TAPPAY_FIELD_IDS.expiry, status.expiry, showIncompleteAsError);
  setTapPayFieldState(TAPPAY_FIELD_IDS.ccv, status.ccv, showIncompleteAsError);
}

function hasTapPayConfig() {
  return Number.isInteger(TAPPAY_CONFIG.appId)
    && TAPPAY_CONFIG.appId > 0
    && typeof TAPPAY_CONFIG.appKey === "string"
    && TAPPAY_CONFIG.appKey.trim() !== "";
}

function validateContactFields(form) {
  const contactFields = ["contact-name", "contact-email", "contact-phone"];

  contactFields.forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.setCustomValidity(field.value.trim() ? "" : "請填寫此欄位");
  });

  if (form.checkValidity()) return true;
  form.reportValidity();
  return false;
}

function getOrderAuthToken() {
  try {
    return localStorage.getItem("token");
  } catch (error) {
    console.error("Unable to read authentication token for order.", error);
    return null;
  }
}

function redirectAfterOrderAuthFailure() {
  try {
    localStorage.removeItem("token");
  } catch (error) {
    console.error("Unable to remove expired authentication token.", error);
  }
  window.location.replace("/");
}

function orderSubmissionError(message) {
  const error = new Error("Unable to create order.");
  error.userMessage = message;
  return error;
}

async function getCurrentBookingForOrder(token) {
  const response = await fetch("/api/booking", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 403) {
    redirectAfterOrderAuthFailure();
    return null;
  }

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw orderSubmissionError(result.message || "無法取得目前的預定行程");
  }
  if (!result.data) {
    throw orderSubmissionError("目前沒有可建立訂單的預定行程");
  }

  return result.data;
}

function buildOrderPayload(prime, booking) {
  return {
    prime,
    order: {
      price: booking.price,
      trip: {
        attraction: {
          id: booking.attraction.id,
          name: booking.attraction.name,
          address: booking.attraction.address,
          image: booking.attraction.image,
        },
        date: booking.date,
        time: booking.time,
      },
      contact: {
        name: document.querySelector("#contact-name").value.trim(),
        email: document.querySelector("#contact-email").value.trim(),
        phone: document.querySelector("#contact-phone").value.trim(),
      },
    },
  };
}

async function handleTapPayPrime(prime) {
  if (typeof prime !== "string" || prime.length === 0) {
    throw new Error("TapPay returned an empty prime.");
  }

  const token = getOrderAuthToken();
  if (!token) {
    redirectAfterOrderAuthFailure();
    return;
  }

  setTapPayMessage("正在建立訂單並處理付款...");
  const booking = await getCurrentBookingForOrder(token);
  if (!booking) return;

  const response = await fetch("/api/orders", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildOrderPayload(prime, booking)),
  });

  if (response.status === 403) {
    redirectAfterOrderAuthFailure();
    return;
  }

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw orderSubmissionError(result.message || "付款失敗，請稍後再試");
  }

  if (
    !result.data?.number
    || !Number.isInteger(result.data.payment?.status)
    || typeof result.data.payment?.message !== "string"
  ) {
    throw orderSubmissionError("付款結果格式不正確，請稍後再試");
  }

  if (result.data.payment.status !== 0) {
    setTapPayMessage(result.data.payment.message);
    return null;
  }

  setTapPayMessage(
    `${result.data.payment.message}，訂單編號：${result.data.number}`,
    "success",
  );
  window.location.assign(`/thankyou?number=${encodeURIComponent(result.data.number)}`);
  return result.data.number;
}

function initializeTapPay() {
  const form = document.querySelector("#booking-content");
  const submitButton = document.querySelector("#booking-checkout-button");
  if (!form || !submitButton) return;

  ["contact-name", "contact-email", "contact-phone"].forEach((fieldId) => {
    document.getElementById(fieldId)?.addEventListener("input", (event) => {
      event.currentTarget.setCustomValidity("");
    });
  });

  if (!hasTapPayConfig()) {
    submitButton.disabled = true;
    setTapPayMessage("TapPay 尚未設定，請先填入 sandbox App ID 與 App Key");
    return;
  }

  if (typeof window.TPDirect === "undefined") {
    submitButton.disabled = true;
    setTapPayMessage("付款元件載入失敗，請重新整理頁面後再試");
    return;
  }

  try {
    window.TPDirect.setupSDK(
      TAPPAY_CONFIG.appId,
      TAPPAY_CONFIG.appKey,
      TAPPAY_CONFIG.serverType,
    );

    window.TPDirect.card.setup({
      fields: {
        number: {
          element: `#${TAPPAY_FIELD_IDS.number}`,
          placeholder: "**** **** **** ****",
        },
        expirationDate: {
          element: `#${TAPPAY_FIELD_IDS.expiry}`,
          placeholder: "MM / YY",
        },
        ccv: {
          element: `#${TAPPAY_FIELD_IDS.ccv}`,
          placeholder: "CVV",
        },
      },
      styles: {
        input: {
          color: "#000000",
          "font-size": "16px",
          "font-family": "Arial, sans-serif",
          "line-height": "36px",
        },
        ":focus": { color: "#000000" },
        ".valid": { color: "#000000" },
        ".invalid": { color: "#d9534f" },
      },
      isMaskCreditCardNumber: true,
      maskCreditCardNumberRange: {
        beginIndex: 6,
        endIndex: 11,
      },
    });

    window.TPDirect.card.onUpdate((update) => {
      updateTapPayFieldStates(update.status);
      if (!update.hasError) setTapPayMessage("");
    });
  } catch (error) {
    console.error("Unable to initialize TapPay.", error);
    submitButton.disabled = true;
    setTapPayMessage("付款元件初始化失敗，請稍後再試");
    return;
  }

  let isGettingPrime = false;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (isGettingPrime || !validateContactFields(form)) return;

    let tappayStatus;
    try {
      tappayStatus = window.TPDirect.card.getTappayFieldsStatus();
    } catch (error) {
      console.error("Unable to read TapPay fields status.", error);
      setTapPayMessage("無法驗證信用卡資料，請重新整理頁面後再試");
      return;
    }

    updateTapPayFieldStates(tappayStatus.status, true);

    if (!tappayStatus.canGetPrime) {
      setTapPayMessage("請確認信用卡資料皆已正確填寫");
      return;
    }

    isGettingPrime = true;
    submitButton.disabled = true;
    setTapPayMessage("正在驗證付款資訊...");

    try {
      window.TPDirect.card.getPrime(async (result) => {
        let orderCreated = false;
        try {
          if (result.status !== 0 || !result.card?.prime) {
            const detail = result.msg ? `：${result.msg}` : "";
            setTapPayMessage(`無法取得付款驗證資料${detail}`);
            return;
          }

          orderCreated = Boolean(await handleTapPayPrime(result.card.prime));
        } catch (error) {
          console.error("Unable to submit order after getting TapPay prime.", error);
          setTapPayMessage(error.userMessage || "訂單建立失敗，請稍後再試");
        } finally {
          isGettingPrime = false;
          submitButton.disabled = orderCreated;
        }
      });
    } catch (error) {
      console.error("Unable to request TapPay prime.", error);
      isGettingPrime = false;
      submitButton.disabled = false;
      setTapPayMessage("無法取得付款驗證資料，請稍後再試");
    }
  });
}

document.addEventListener("DOMContentLoaded", initializeTapPay);
