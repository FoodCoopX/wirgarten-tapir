var initSummary = (harvest_share_prices) => {

    const calculatePrice = (harvest_share) => {
                const [key, price] = harvest_share.split(':');
                return document.getElementsByName('Harvest Shares-' +key)[0].value * price;
    };

    const resultElem = document.getElementById('harvest_shares_total');
    const soliElem = document.getElementById('id_Harvest Shares-solidarity_price');

    const calculateTotal = () => {
        return harvest_share_prices.split(',').map(calculatePrice).reduce((a,b) => a + b) * (1 + parseFloat(soliElem.value));
    }

    const handleChange = (event, max_shares) => {
        if(event && max_shares){
            if(event.target.value < 0){
                event.target.value = 0;
            } else if (event.target.value > max_shares){
                event.target.value = max_shares;
            }
        }

        resultElem.innerText = calculateTotal().toFixed(2);
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