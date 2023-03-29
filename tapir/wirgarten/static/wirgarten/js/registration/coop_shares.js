const initSummary = (min_shares, share_price) => {
    const resultElem = document.getElementById('cooperative_shares_total');
    const input = document.getElementsByName('Cooperative Shares-cooperative_shares')[0];
    input.step = 50;
    input.min = input.value = min_shares * share_price;

    input.addEventListener('change', event => {
        if(event.target.value < input.min){
            input.value = input.min;
        }
    });

    const handleChange = () => {
        const diff = input.value % 50
        if(diff > 0){
            const fallback = diff > 24 ? Number(input.value) + (50 - diff) : input.value - diff;
            input.value = Math.max(fallback, input.min)
        }

        resultElem.innerText = input.value;
    }

    handleChange();

    input.addEventListener('change', handleChange);
}