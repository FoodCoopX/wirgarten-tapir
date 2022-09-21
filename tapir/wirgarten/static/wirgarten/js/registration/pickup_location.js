var initMap = coords => {
    const pickupLocationSelect = document.getElementById('id_Pickup Location-pickup_location');

    const markers = {};
    const idToCoords = (id) => coords[id].split(',')
    const map = L.map('map').setView(idToCoords(pickupLocationSelect.options[0].value), 10);

    for(let i = 0; i < pickupLocationSelect.options.length; i++) {
        const option = pickupLocationSelect.options[i]
        const marker = L.marker(idToCoords(option.value)).addTo(map);
        marker.bindPopup("<b>" + option.innerText.replaceAll(",","<br/>").replaceAll(" (","<br/><br/>(").replace("<br/>","</b><br/>") );
        marker.locationId = option.value;
        marker.on("click", e => handleSelect(e.target.locationId));

        markers[option.value] = marker;
      }

    const handleSelect = (id) => {
        pickupLocationSelect.value = id;

        map.flyTo(idToCoords(id), 14);

        // reset marker colors
        Object.values(markers).forEach(m => m._icon.style.webkitFilter = "");

        const marker = markers[id];
        marker.openPopup();
        marker._icon.style.webkitFilter = "hue-rotate(160deg)";
     }

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);

    handleSelect(pickupLocationSelect.options[0].value);
    pickupLocationSelect.addEventListener("change", ({ target }) =>  handleSelect(target.value));
}