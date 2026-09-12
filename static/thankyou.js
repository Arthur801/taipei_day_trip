function getOrderToken() {
  try {
    return localStorage.getItem("token");
  } catch (error) {
    console.error("Unable to read authentication token for order details.", error);
    return null;
  }
}

function setOrderMessage(message) {
  const messageElement = document.querySelector("#order-message");
  if (messageElement) messageElement.textContent = message;
}

function renderOrderDetails(order) {
  const detailsElement = document.querySelector("#order-details");
  const attraction = order.trip?.attraction;
  const contact = order.contact;

  if (!detailsElement || !attraction || !contact) {
    throw new Error("Order API returned incomplete data.");
  }

  const timeText = order.trip.time === "afternoon"
    ? "下午 2 點到晚上 9 點"
    : "早上 9 點到下午 4 點";
  const price = Number(order.price);

  document.querySelector("#order-attraction").textContent = attraction.name || "";
  document.querySelector("#order-date").textContent = (order.trip.date || "").replaceAll("-", "/");
  document.querySelector("#order-time").textContent = timeText;
  document.querySelector("#order-price").textContent = Number.isFinite(price)
    ? `新台幣 ${price.toLocaleString("zh-TW")} 元`
    : "";
  document.querySelector("#order-address").textContent = attraction.address || "";
  document.querySelector("#order-contact-name").textContent = contact.name || "";
  document.querySelector("#order-contact-email").textContent = contact.email || "";
  document.querySelector("#order-contact-phone").textContent = contact.phone || "";
  document.querySelector("#order-status").textContent = order.status === 1 ? "付款成功" : "尚未付款";

  detailsElement.hidden = false;
  setOrderMessage("");
}

async function loadOrderDetails(orderNumber) {
  const token = getOrderToken();
  if (!token) {
    setOrderMessage("無法取得訂單資訊，請先登入系統");
    return;
  }

  setOrderMessage("正在載入訂單資訊...");

  try {
    const response = await fetch(`/api/order/${encodeURIComponent(orderNumber)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const result = await response.json().catch(() => ({}));

    if (response.status === 403) {
      setOrderMessage("登入狀態已失效，請重新登入後查看訂單");
      return;
    }
    if (!response.ok) {
      throw new Error(result.message || `Unable to load order: ${response.status}`);
    }
    if (!result.data) {
      setOrderMessage("找不到此訂單資訊");
      return;
    }

    renderOrderDetails(result.data);
  } catch (error) {
    console.error("Unable to load order details.", error);
    setOrderMessage("訂單資訊載入失敗，請稍後再試");
  }
}

function initializeThankYouPage() {
  const orderNumberElement = document.querySelector("#order-number");
  if (!orderNumberElement) return;

  const orderNumber = new URLSearchParams(window.location.search).get("number");
  if (!orderNumber) {
    orderNumberElement.textContent = "無法取得訂單編號";
    setOrderMessage("網址中缺少訂單編號");
    return;
  }

  orderNumberElement.textContent = orderNumber;
  loadOrderDetails(orderNumber);
}

document.addEventListener("DOMContentLoaded", initializeThankYouPage);
