let soliElem = document.getElementById('id_Harvest Shares-solidarity_price_harvest_shares');
const origOptions = [...soliElem.options]

const calculatePrice = (harvest_share) => {
    const [key, price] = harvest_share.split(':');
    return document.getElementsByName('Harvest Shares-' +key)[0].value * price;
};

var initSummary = (harvest_share_prices, solidarity_total, capacity_total) => {
    const resultElem = document.getElementById('harvest_shares_total');

    const calculateTotalWithoutSoliPrice = () => harvest_share_prices.split(',').map(calculatePrice).reduce((a,b) => a + b);
    const calculateTotal = () => calculateTotalWithoutSoliPrice() * (1 + parseFloat(soliElem.value));

    const handleChange = (event, max_shares) => {
        if(event && max_shares){
            if(event.target.value < 0){
                event.target.value = 0;
            } else if (event.target.value > max_shares){
                event.target.value = max_shares;
            }
        }

        while(calculateTotalWithoutSoliPrice() > capacity_total){
             event.target.value--;
         }

        resultElem.innerText = calculateTotal().toFixed(2);

        console.log(event)
        filterSoliPriceOptions(calculateTotalWithoutSoliPrice(), solidarity_total);
    }

    const filterSoliPriceOptions = (shares_total, solidarity_total) => {
        const selected = soliElem.value;
        options = [...origOptions].filter(o => {
            const value = parseFloat(o.value)
            return value >= 0 || (-value * shares_total) < solidarity_total;
        })

        while(soliElem.firstChild){
            soliElem.removeChild(soliElem.firstChild);
        }

        const newSelectEl = soliElem.cloneNode(true);

        for (option of options){
            newSelectEl.appendChild(option)
        }

        soliElem.parentNode.replaceChild(newSelectEl, soliElem);
        soliElem = newSelectEl;
        soliElem.value = selected;
        soliElem.addEventListener("change", handleChange);
    };

    let noCapacity = true;
    harvest_share_prices.split(',').forEach(harvest_share => {
        const [key,price] = harvest_share.split(":");
        const input = document.getElementsByName('Harvest Shares-' + key)[0];
        input.addEventListener('change', e => handleChange(e, 10));
        input.min = 0;
        input.max = Math.max(0,Math.min(10, Math.floor(capacity_total / parseFloat(price))))
        if(input.max == 0){
            input.readOnly=true;
            input.value=0;
        } else {
            noCapacity = false;
        }
    });

    if(noCapacity){
        soliElem.readOnly=true;
        document.getElementById('no-capacity-warning').style.display='block';
    }

    handleChange();
}