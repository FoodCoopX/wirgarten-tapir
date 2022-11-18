var initSummary = bestellcoop_price => {

    const resultElem = document.getElementById('bestellcoop_total');
    const checkbox = document.getElementById('id_BestellCoop-bestellcoop');

    const handleChange = () => {
        resultElem.innerText = (checkbox.checked ? bestellcoop_price : 0).toFixed(2);
    }

    checkbox.addEventListener('change', handleChange);

    handleChange();
}