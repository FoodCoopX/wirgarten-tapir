var initMap = (data, productTypes = [], callback = false) => {
    // FIXME: the select box from the widget should be decoupled from the map
    const pickupLocationSelect = document.getElementById('id_pickup_location');
    if(pickupLocationSelect) pickupLocationSelect.required = true;

    const markers = {};
    const idToCoords = (id) => {
        return data[id]["coords"].split(',')
    }
    const map = L.map('map').setView(idToCoords(Object.entries(data)[0][0]), 12);

    const possibleLocations = pickupLocationSelect ? Array.from(pickupLocationSelect.options).map(o => o.value) : Object.keys(data)

     const setMarkerColor = (marker) => {
         if(!possibleLocations.includes(marker.locationId)){
            marker._icon.style.webkitFilter = "grayscale()"
        } else {
         marker._icon.style.webkitFilter = ""
        }
    }

    for(const [id, pl] of Object.entries(data)) {
        const marker = L.marker(idToCoords(id)).addTo(map);
        console.log("pl", pl)
        const missingCapabilities = productTypes.filter(v => !pl.capabilities.map(it => it.name).includes(v))
        marker.bindPopup(`<div style="text-align: center">
        <strong>${pl.name}</strong>
            <br/>
                ${pl.street}, ${pl.city}<br/></br>
                <small>${pl.info.replace(',', ', <br/>')}</small><br/>
                <br/>
                ${pl.capabilities.map(c =>
                    `<span title="${c}" style="font-size:2.5em; text-decoration:strikethrough;">${c.icon}</span>`
                ).join(" ")}

                ${missingCapabilities.length == 0 ? '' : `<br/><span style="color:darkred">Folgende Produkte sind hier leider <strong>nicht</strong> abholbar: ${missingCapabilities.join(" ")}<br/></span>`}
            </div>
            `);
        marker.locationId = id;
        marker.riseOnHover = true;
        marker.on("click", e => select(e.target.locationId, callback));
        setMarkerColor(marker)

        markers[id] = marker;
      }

    const select = (id, callback) => {
        if(pickupLocationSelect) pickupLocationSelect.value = id;

        target = idToCoords(id)
        target[0] = parseFloat(target[0]) + 0.002
        map.flyTo(target, 14 )

        // reset marker colors
        Object.values(markers).forEach(setMarkerColor);

        const marker = markers[id];
        marker.openPopup();
        marker._icon.style.webkitFilter = "hue-rotate(160deg)";

        if(callback){
            callback(id)
        }
     }

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);

    if(pickupLocationSelect){
        select(pickupLocationSelect.options[0].value);
        pickupLocationSelect.addEventListener("change", ({ target }) =>  select(target.value));
    }

    return (id) => select(id, false)
}