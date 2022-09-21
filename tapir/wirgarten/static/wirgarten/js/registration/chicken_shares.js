var initSummary = (max_shares, chicken_share_prices) => {

    const calculatePrice = (chicken_share) => {
        const [key, price] = chicken_share.split(':');
        return document.getElementsByName('Additional Shares-' + key)[0].value * price;
    };

    const resultElem = document.getElementById('additional_shares_total');

    const calculateTotal = () => {
        return chicken_share_prices.map(calculatePrice).reduce((a,b) => a + b);
    }

    const handleChange = (event) => {
        if(event){
            if(event.target.value > max_shares){
                event.target.value = max_shares
            } else if(event.target.value < 0){
                event.target.value = 0
            }
        }

        resultElem.innerText = calculateTotal().toFixed(2);
    }

    chicken_share_prices.forEach(chicken_share => {
        const key = chicken_share.split(":")[0];
        const input = document.getElementsByName('Additional Shares-' + key)[0];
        input.max = max_shares;
        input.addEventListener('change', handleChange);
    });

    handleChange();
}