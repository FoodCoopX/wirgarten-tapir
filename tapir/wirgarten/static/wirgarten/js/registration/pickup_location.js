function initMap(
  data,
  productTypes = {},
  callback = false,
  selected = undefined,
) {
  const markerIcon = L.icon({
    iconRetinaUrl: "/static/wirgarten/images/leaflet/marker-icon-2x.png",
    iconUrl: "/static/wirgarten/images/leaflet/marker-icon.png",
    shadowUrl: "/static/wirgarten/images/leaflet/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });

  const markers = {};
  const idToCoords = (id) => {
    return data[id]["coords"].split(",");
  };
  const idsWithCoords = Object.keys(data).filter((id) => data[id]["coords"]);
  const map = L.map("map");
  if (idsWithCoords.length > 0) {
    map.setView(idToCoords(idsWithCoords[0]), 12);
  } else {
    map.setView([51.16, 10.45], 6);
  }

  const possibleLocations = new Set(Object.keys(data));

  const setMarkerColor = (marker) => {
    if (possibleLocations.has(marker.locationId)) {
      marker._icon.style.webkitFilter = "";
    } else {
      marker._icon.style.webkitFilter = "grayscale()";
    }
  };

  for (const [id, pl] of Object.entries(data)) {
    if (!pl.coords) continue;
    const marker = L.marker(idToCoords(id), { icon: markerIcon }).addTo(map);

    marker.bindPopup(`<div style="text-align: center">
        <strong>${pl.name}</strong>
            <br/>
                ${pl.street}, ${pl.city}<br/>
                ${pl.opening_times}
            </div>
            `);
    marker.locationId = id;
    marker.riseOnHover = true;
    marker.on("click", (e) => select(e.target.locationId, callback));
    setMarkerColor(marker);

    markers[id] = marker;
  }

  const select = (id, callback = false) => {
    if (!data[id] || !markers[id]) return;

    const target = idToCoords(id);
    target[0] = Number.parseFloat(target[0]) + 0.002;
    map.flyTo(target, 14);

    // reset marker colors
    Object.values(markers).forEach(setMarkerColor);

    const marker = markers[id];
    marker.openPopup();
    marker._icon.style.webkitFilter = "hue-rotate(160deg)";

    if (callback) {
      callback(id);
    }
  };

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap",
    referrerPolicy: "no-referrer-when-downgrade",
  }).addTo(map);

  if (selected !== undefined) {
    select(selected);
  }

  return (id) => select(id);
}
