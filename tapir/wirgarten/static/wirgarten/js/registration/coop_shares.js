const initSummary = (min_shares, share_price) => {
    const resultElem = document.getElementById('cooperative_shares_total');
    const input = document.getElementsByName('Cooperative Shares-cooperative_shares')[0];
    input.min = input.value = min_shares;

    input.addEventListener('change', event => {
        console.log(event.target.value , min_shares)
        if(event.target.value < min_shares){
            input.value = min_shares;
        }
    });

    const handleChange = () => {
        let sum = input.value * share_price;
        resultElem.innerText = sum.toFixed(2);
    }

    handleChange();

    input.addEventListener('change', handleChange);
}