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
  const attractionGroup = document.querySelector(".attractions-group");
  if (!attractionGroup) return;

  try {
    const response = await fetch("/api/attractions?page=0");
    if (!response.ok) throw new Error(`Unable to load attractions: ${response.status}`);

    const { data } = await response.json();
    attractionGroup.replaceChildren(...data.map(createAttractionCard));
  } catch (error) {
    console.error("Unable to load attractions.", error);
  }
}

document.addEventListener("DOMContentLoaded", loadAttractions);
