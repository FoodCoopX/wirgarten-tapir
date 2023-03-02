var initBestellCoopSummary = bestellcoop_price => {

    const resultElem = document.getElementById('bestellcoop_total');
    let checkbox = document.getElementsByName('bestellcoop')[0];
    if(!checkbox){
        checkbox = document.getElementsByName('BestellCoop-bestellcoop')[0];
    }

    const handleChange = () => {
        resultElem.innerText = (checkbox.checked ? bestellcoop_price : 0).toFixed(2);
    }

    checkbox.addEventListener('change', handleChange);

    handleChange();
}