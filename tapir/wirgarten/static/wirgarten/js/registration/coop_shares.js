const initSummary = (min_shares, share_price) => {
    const resultElem = document.getElementById('cooperative_shares_total');
    let input = document.getElementsByName('Cooperative Shares-cooperative_shares')[0];
    if(!input){
        input = document.getElementsByName('cooperative_shares')[0];
    }
    input.step = 50;
    input.min = input.value = min_shares * share_price;

    input.addEventListener('change', event => {
        if(event.target.value < input.min){
            input.value = input.min;
        }
    });

    const handleChange = (evt) => {
        const value = evt.target.value
        const diff = value % 50
        if(diff > 0){
            const fallback = diff > 24 ? Number(value) + (50 - diff) : value - diff;
            console.log(diff, fallback)
            input.value = Math.max(fallback, input.min)
        }

        resultElem.innerText = input.value;
    }

    resultElem.innerText = input.value;
    input.addEventListener('change', handleChange);
}