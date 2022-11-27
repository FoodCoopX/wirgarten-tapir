var initSummary = (max_shares, chicken_share_prices, capacity_total) => {
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

         while(calculateTotal() > capacity_total){
             event.target.value--;
         }

        resultElem.innerText = calculateTotal().toFixed(2);
    }

    chicken_share_prices.forEach(chicken_share => {
        const [key,price] = chicken_share.split(":");
        const input = document.getElementsByName('Additional Shares-' + key)[0];

        input.max = Math.max(0,Math.min(max_shares, Math.floor(capacity_total / price)))
        input.addEventListener('change', handleChange);
    });

    handleChange();
}