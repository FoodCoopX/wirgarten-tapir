var initChickenShareSummary = (chicken_share_prices, capacity_total) => {
    const calculatePrice = (chicken_share) => {
        const [key, price] = chicken_share.split(':');
        let elem = document.getElementsByName('Additional Shares-' + key)[0];
        if(!elem){
            elem = document.getElementsByName(key)[0]
        }
        return elem.value * price;
    };

    const resultElem = document.getElementById('additional_shares_total');

    const calculateTotal = () => {
        return chicken_share_prices.map(calculatePrice).reduce((a,b) => a + b);
    }

    const handleChange = (event) => {
        if(event){
            const value = parseInt(event.target.value)
            const max = parseInt(event.target.max)
            if(value < 0){
                event.target.value = 0
            } else if (value > max){
                event.target.value = event.target.max
            }
        }

         while(calculateTotal() > capacity_total){
             event.target.value--;
         }

        resultElem.innerText = calculateTotal().toFixed(2);
    }

    chicken_share_prices.forEach(chicken_share => {
        const [key,price] = chicken_share.split(":");
        let input = document.getElementsByName('Additional Shares-' + key)[0];
        if(!input){
            input = document.getElementsByName(key)[0]
        }

        input.max = Math.max(0, Math.floor(capacity_total / price))

        if(input.max == 0){
            input.readOnly=true;
            input.value=0;
        }

        input.addEventListener('change', handleChange);
    });

    handleChange();
}