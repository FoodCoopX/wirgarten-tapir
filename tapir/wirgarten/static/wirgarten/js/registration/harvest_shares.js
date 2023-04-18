let soliElem = document.getElementsByName('solidarity_price_harvest_shares')[0];
if(!soliElem){
    soliElem = document.getElementsByName('Harvest Shares-solidarity_price_harvest_shares')[0];
}
const origOptions = [...soliElem.options]

const calculatePrice = (harvest_share) => {
    const [key, price] = harvest_share.split(':');
    let elem = document.getElementsByName('Harvest Shares-' +key)[0]
    if(!elem){
        elem = document.getElementsByName(key)[0]
    }
    return elem.value * price;
};

var initHarvestShareSummary = (harvest_share_prices, solidarity_total, capacity_total) => {
    const resultElem = document.getElementById('harvest_shares_total');

    let customSoliElem = document.getElementById('id_solidarity_price_absolute_harvest_shares')
    if (!customSoliElem) {
        customSoliElem = document.getElementById('id_Harvest Shares-solidarity_price_absolute_harvest_shares')
    }


    const calculateTotalWithoutSoliPrice = () => harvest_share_prices.split(',').map(calculatePrice).reduce((a, b) => a + b);
    const calculateTotal = () => calculateTotalWithoutSoliPrice() * (1 + parseFloat(soliElem.value));

    const handleChange = (event, max_shares) => {
        if (event && max_shares) {
            if (event.target.value < 0) {
                event.target.value = 0;
            } else if (event.target.value > max_shares) {
                event.target.value = max_shares;
            }
        }

        while(calculateTotalWithoutSoliPrice() > capacity_total){
             event.target.value--;
         }

        resultElem.innerText = calculateTotal().toFixed(2);

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

        const optArr = Array.from(options)
        const newSelected = optArr.some(o => o.value === selected) ? selected : optArr[optArr.length - 1].value;

        soliElem.value = newSelected;

        resultElem.innerText = calculateTotal().toFixed(2);
        soliElem.addEventListener("change", handleChange);
    };

    let noCapacity = true;
    harvest_share_prices.split(',').forEach(harvest_share => {
        const [key,price] = harvest_share.split(":");
        let input = document.getElementsByName('Harvest Shares-' + key)[0];
        if(!input){
            input = document.getElementsByName(key)[0];
        }
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