// FIXME: maybe we need a new field in product type for the icon
const PRODUCT_TYPE_ICONS = {
    "Ernteanteile": "🌾",
    "Hühneranteile": "🐔"
}

var initMap = (data, productTypes) => {
    const pickupLocationSelect = document.getElementById('id_pickup_location');
    pickupLocationSelect.required = true;

    const markers = {};
    const idToCoords = (id) => data[id]["coords"].split(',')
    const map = L.map('map').setView(idToCoords(pickupLocationSelect.options[0].value), 10);

    const possibleLocations = Array.from(pickupLocationSelect.options).map(o => o.value)

     const setMarkerColor = (marker) => {
         if(!possibleLocations.includes(marker.locationId)){
            marker._icon.style.webkitFilter = "grayscale()"
        } else {
         marker._icon.style.webkitFilter = ""
        }
    }

    for(const [id, pl] of Object.entries(data)) {
        const marker = L.marker(idToCoords(id)).addTo(map);
        const missingCapabilities = productTypes.filter(v => !pl.capabilities.includes(v))
        marker.bindPopup(`<div style="text-align: center">
        <strong>${pl.name}</strong>
            <br/>
                ${pl.street}, ${pl.city}<br/></br>
                <small>${pl.info}</small><br/>
                <br/>
                ${pl.capabilities.map(c =>
                    `<span title="${c}" style="font-size:2.5em; text-decoration:strikethrough;">${PRODUCT_TYPE_ICONS[c]}</span>`
                ).join(" ")}

                ${missingCapabilities.length == 0 ? '' : `<br/><span style="color:darkred">Folgende Produkte sind hier leider <strong>nicht</strong> abholbar: ${missingCapabilities.join(" ")}<br/></span>`}

            </div>
            `);
        marker.locationId = id;
        marker.riseOnHover = true;
        marker.on("click", e => handleSelect(e.target.locationId));
        setMarkerColor(marker)

        markers[id] = marker;
      }

    const handleSelect = (id) => {
        pickupLocationSelect.value = id;

        target = idToCoords(id)
        target[0] = parseFloat(target[0]) + 0.002
        map.flyTo(target, 14 )

        // reset marker colors
        Object.values(markers).forEach(setMarkerColor);

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