const RESOURCE_ORIGIN = "https://padax.github.io/taipei-day-trip-resources";

function getAttractionId() {
  const match = window.location.pathname.match(/^\/attraction\/([1-9]\d*)\/?$/);
  return match ? match[1] : null;
}

function getImageUrl(imagePath) {
  if (!imagePath) return "";
  return imagePath.startsWith("http") ? imagePath : `${RESOURCE_ORIGIN}${imagePath}`;
}

function formatAttractionText(text) {
  return String(text || "")
    .replace(/。\s*/g, "。\n")
    .replace(/\s*([•●▪◦‧・])/g, "\n$1")
    .trim();
}

function renderFormattedText(element, text) {
  const lines = formatAttractionText(text).split(/\n+/).filter(Boolean);
  if (lines.length < 2) {
    element.textContent = lines[0] || "";
    return;
  }

  element.replaceChildren(...lines.map((line) => {
    const textLine = document.createElement("span");
    textLine.className = "attraction-text-line";
    textLine.textContent = line;
    return textLine;
  }));
}

function renderGallery(images, attractionName) {
  const gallery = document.querySelector("#attraction-images");
  const previousButton = document.querySelector("#previous-image");
  const nextButton = document.querySelector("#next-image");
  const indicators = document.querySelector("#image-indicators");
  const validImages = images.filter((image) => typeof image === "string" && image);

  if (!gallery || !previousButton || !nextButton || !indicators) return;
  if (validImages.length === 0) {
    previousButton.hidden = true;
    nextButton.hidden = true;
    indicators.replaceChildren();
    return;
  }

  const image = document.createElement("img");
  image.className = "attraction-gallery-image";
  image.alt = attractionName;
  const indicatorButtons = validImages.map((_, index) => {
    const button = document.createElement("button");
    button.className = "gallery-indicator";
    button.type = "button";
    button.setAttribute("aria-label", `顯示第 ${index + 1} 張圖片`);
    return button;
  });
  let currentIndex = 0;

  function showImage(index) {
    currentIndex = (index + validImages.length) % validImages.length;
    image.src = getImageUrl(validImages[currentIndex]);
    indicatorButtons.forEach((button, buttonIndex) => {
      const isActive = buttonIndex === currentIndex;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-current", String(isActive));
    });
  }

  previousButton.hidden = validImages.length < 2;
  nextButton.hidden = validImages.length < 2;
  previousButton.onclick = () => showImage(currentIndex - 1);
  nextButton.onclick = () => showImage(currentIndex + 1);
  indicatorButtons.forEach((button, index) => button.addEventListener("click", () => showImage(index)));
  indicators.replaceChildren(...indicatorButtons);
  gallery.prepend(image);
  showImage(0);
}

function renderAttraction(attraction) {
  document.querySelector("#attraction-name").textContent = attraction.name || "";
  document.querySelector("#attraction-category").textContent = attraction.category || "";
  document.querySelector("#attraction-mrt").textContent = attraction.mrt || "";
  renderFormattedText(document.querySelector("#attraction-description"), attraction.description);
  renderFormattedText(document.querySelector("#attraction-address"), attraction.address);
  renderFormattedText(document.querySelector("#attraction-transport"), attraction.transport);
  document.title = attraction.name ? `台北一日遊｜${attraction.name}` : "台北一日遊｜景點";
  renderGallery(Array.isArray(attraction.images) ? attraction.images : [], attraction.name || "景點圖片");
}

function initializeBookingTime() {
  const timeOptions = document.querySelectorAll('input[name="booking-time"]');
  const price = document.querySelector(".booking-price");
  if (!price || timeOptions.length === 0) return;

  function updatePrice() {
    const selectedTime = document.querySelector('input[name="booking-time"]:checked');
    const amount = selectedTime?.value === "afternoon" ? 2500 : 2000;
    const label = document.createElement("strong");
    label.textContent = "導覽費用：";
    price.replaceChildren(label, `新台幣 ${amount} 元`);
  }

  timeOptions.forEach((option) => option.addEventListener("change", updatePrice));
  updatePrice();
}

async function loadAttraction() {
  const attractionId = getAttractionId();
  if (!attractionId) {
    console.error("Invalid attraction URL.");
    return;
  }

  try {
    const response = await fetch(`/api/attraction/${attractionId}`);
    if (!response.ok) throw new Error(`Unable to load attraction: ${response.status}`);
    const { data } = await response.json();
    if (!data) throw new Error("Attraction API returned no data.");
    renderAttraction(data);
  } catch (error) {
    console.error("Unable to load attraction.", error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initializeBookingTime();
  loadAttraction();
});
