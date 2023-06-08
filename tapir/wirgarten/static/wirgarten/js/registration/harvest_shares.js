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
    if(!customSoliElem){
        customSoliElem = document.getElementById('id_Harvest Shares-solidarity_price_absolute_harvest_shares')
    }

    const calculateTotalWithoutSoliPrice = () => harvest_share_prices.split(',').map(calculatePrice).reduce((a,b) => a + b);
    const calculateTotal = () => {
        if(soliElem.value === 'custom'){
            return calculateTotalWithoutSoliPrice() + parseFloat(customSoliElem.value);
        } else  {
            return calculateTotalWithoutSoliPrice() * (1 + parseFloat(soliElem.value));
        }
    }
    const warningCannotReduceElem = document.getElementById("warning-cannot-reduce")
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
        const totalWithoutSoli = calculateTotalWithoutSoliPrice()
        if (soliElem.value === 'custom'){
            customSoliElem.disabled = false
            customSoliElem.required = true
        } else {
            customSoliElem.disabled = true
            customSoliElem.value = (totalWithoutSoli * soliElem.value).toFixed(2)
        }

        filterSoliPriceOptions(totalWithoutSoli, solidarity_total);

        const submitBtn = document.getElementById('submit-btn')
        if(totalWithoutSoli < originalTotal){
            if(submitBtn) {submitBtn.disabled=true}
            warningCannotReduceElem.style.display = "block";
        } else{
            if(submitBtn) {submitBtn.disabled=false}
            warningCannotReduceElem.style.display = "none";
        }
    }

    customSoliElem.addEventListener('change', e => {
        if(e.target.value === 0 || e.target.value === NaN) {
            e.target.value = 0;
        }

        if(e.target.value < 0){
            e.target.value = 0;
        }

        e.target.value = parseFloat(e.target.value).toFixed(2);

        handleChange(e)
        }
    );

    const filterSoliPriceOptions = (shares_total, solidarity_total) => {
        const selected = soliElem.value;

        options = [...origOptions].filter(o => {
            if(o.value === 'custom'){
                return true;
            }

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
        soliElem.addEventListener("change", e => {
            // if the value is 'custom', we set the value of the custom input to the price without solidarity + at least 10€ + difference to get a round sum (10)
            if(e.target.value === 'custom'){
                    const priceWithoutSoli = calculateTotalWithoutSoliPrice()
                    customSoliElem.value = ((priceWithoutSoli + 20) - ((priceWithoutSoli) % 10) - priceWithoutSoli).toFixed(2)
            }

            handleChange(e)
        });
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
        noCapacityWarningElem = document.getElementById('no-capacity-warning')
        if (noCapacityWarningElem) noCapacityWarningElem.style.display='block';
    }

    resultElem.innerText = calculateTotal().toFixed(2);
}