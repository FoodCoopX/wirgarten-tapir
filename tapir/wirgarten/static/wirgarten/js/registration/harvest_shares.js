const soliElem = document.getElementById('id_Harvest Shares-solidarity_price');
const origOptions = [...soliElem.options]

const calculatePrice = (harvest_share) => {
    const [key, price] = harvest_share.split(':');
    return document.getElementsByName('Harvest Shares-' +key)[0].value * price;
};

const filterSoliPriceOptions = (shares_total, solidarity_total) => {
    options = [...origOptions].filter(o => {
        const value = parseFloat(o.value)
        return value >= 0 || (-value * shares_total) < solidarity_total;
    })

    for (let i = 0; i < soliElem.options.length; i++){
        soliElem.options.remove(i);
    }

    for (let o of options){
        soliElem.options.add(o);
    }
};

var initSummary = (harvest_share_prices, solidarity_total) => {
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

        resultElem.innerText = calculateTotal().toFixed(2);

        filterSoliPriceOptions(calculateTotalWithoutSoliPrice(), solidarity_total);
    }

    harvest_share_prices.split(',').forEach(harvest_share => {
        const [key,price] = harvest_share.split(":");
        const input = document.getElementsByName('Harvest Shares-' + key)[0];
        input.addEventListener('change', e => handleChange(e, 10));
        input.min = 0
        input.max = 10
    });
    soliElem.addEventListener('change', handleChange);

    handleChange();
}