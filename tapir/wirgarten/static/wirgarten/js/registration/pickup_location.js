var initMap = (data, productTypes = [], callback = false, selected = undefined) => {
    const markers = {};
    const idToCoords = (id) => {
        return data[id]["coords"].split(',')
    }
    const map = L.map('map').setView(idToCoords(Object.entries(data)[0][0]), 12);

    const possibleLocations = Object.keys(data)

     const setMarkerColor = (marker) => {
         if(!possibleLocations.includes(marker.locationId)){
            marker._icon.style.webkitFilter = "grayscale()"
        } else {
         marker._icon.style.webkitFilter = ""
        }
    }

    for(const [id, pl] of Object.entries(data)) {
        const marker = L.marker(idToCoords(id)).addTo(map);
        const missingCapabilities = productTypes.filter(v => !pl.capabilities.map(it => it.name).includes(v))
        marker.bindPopup(`<div style="text-align: center">
        <strong>${pl.name}</strong>
            <br/>
                ${pl.street}, ${pl.city}<br/></br>
                <small>${pl.info.replace(',', ', <br/>')}</small><br/>
                <br/>
                ${pl.capabilities.map(c =>
                    `<span title="${c.name}" style="font-size:2.5em; text-decoration:strikethrough;">${c.icon}</span>`
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

    const select = (id, callback = false) => {
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

    if(selected !== undefined){
        select(selected)
    }

    return (id) => select(id)
}