const regex =  /https:\/\/(?:www\.)?google\.[a-z]{2,6}\/maps\/place\/(.*)\/@(\d{1,2}\.\d*,\d{1,2}\.\d*),\d*\.?\d*z\//

    const nameInput = document.getElementById("id_name")
    const coordsInput = document.getElementById("id_coords")
    const streetInput = document.getElementById("id_street")
    const postcodeInput = document.getElementById("id_postcode")
    const cityInput = document.getElementById("id_city")

    const gmapsLinkElem = document.getElementById("id_gmaps");
    const gmapsAddressElem = document.getElementById("id_gmaps_address");

    gmapsAddressElem.addEventListener("input", (e) => {
        const address = e.target.value;

        const split = address.split(/[,\n]/);
        const street = split[0];
        const [postcode, city] = split[1].trim().split(" ");

        streetInput.value = street.trim();
        postcodeInput.value = postcode.trim();
        cityInput.value = city.trim();
    });

    gmapsLinkElem.addEventListener("input", (e) => {
        const link = e.target.value;

        console.log(link, regex.test(link))

        if(regex.test(link)){
            const match = regex.exec(link)
            const name = decodeURI(match[1]).replaceAll('+', ' ');
            const coords = match[2];

            nameInput.value = name;
            coordsInput.value = coords;
        }
    });

const initCapas = (productTypes) => {
    for (const id of productTypes){
        const checkbox = document.getElementById(`id_pt_${id}`);
        const capaInput = document.getElementById(`id_pt_capa_${id}`);

        capaInput.disabled = !checkbox.checked;

        const handleCheck = () => {
            if(checkbox.checked){
                capaInput.disabled = false;
            } else {
                capaInput.disabled = true;
            }
        }

        checkbox.addEventListener("change", handleCheck);
    }
}