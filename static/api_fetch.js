let nextPage = 0;
let isLoading = false;
let attractionGroup;
let moreObserver;

function createAttractionCard(attraction) {
  const card = document.createElement("article");
  card.className = "attraction-card";

  const image = document.createElement("img");
  image.src = attraction.images[0]
    ? `https://padax.github.io/taipei-day-trip-resources${attraction.images[0]}`
    : "";
  image.alt = attraction.name;

  const name = document.createElement("h3");
  name.className = "attraction-name";
  name.textContent = attraction.name;

  const information = document.createElement("footer");
  information.className = "attraction-info";

  const mrt = document.createElement("span");
  mrt.textContent = attraction.mrt || "";

  const category = document.createElement("span");
  category.textContent = attraction.category;

  information.append(mrt, category);
  card.append(image, name, information);
  return card;
}

async function loadAttractions() {
  if (isLoading || nextPage === null) return;

  isLoading = true;
  const page = nextPage;

  try {
    const response = await fetch(`/api/attractions?page=${page}`);
    if (!response.ok) throw new Error(`Unable to load attractions: ${response.status}`);

    const { data, nextPage: returnedNextPage } = await response.json();
    attractionGroup.append(...data.map(createAttractionCard));
    nextPage = returnedNextPage;
    if (nextPage === null && moreObserver) moreObserver.disconnect();
  } catch (error) {
    console.error("Unable to load attractions.", error);
  } finally {
    isLoading = false;
  }
}

function observeMoreAttractions() {
  const loadMoreTrigger = document.createElement("div");
  loadMoreTrigger.setAttribute("aria-hidden", "true");
  attractionGroup.after(loadMoreTrigger);

  moreObserver = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) loadAttractions();
  });
  moreObserver.observe(loadMoreTrigger);
}

document.addEventListener("DOMContentLoaded", async () => {
  attractionGroup = document.querySelector(".attractions-group");
  if (!attractionGroup) return;

  await loadAttractions();
  if (nextPage !== null) observeMoreAttractions();
});
