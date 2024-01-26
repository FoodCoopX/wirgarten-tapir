var initAdditionalShareSummary = (additional_share_prices, capacity_total) => {
  console.log(additional_share_prices)
  const calculatePrice = (chicken_share) => {
    const [key, price] = chicken_share.split(":");
    const elem = document.querySelector(
      `[name$='${key}']`
    );
    console.log(key, price, elem)

    if (!elem) return 0;
    let value = 0;
    if (elem.type == "checkbox") {
      value = elem.checked ? 1 : 0;
    } else {
      value = elem.value;
    }
    return value * price;
  };

  const resultElem = document.getElementById("additional_shares_total");

  const calculateTotal = () => {
    return additional_share_prices.map(calculatePrice).reduce((a, b) => a + b);
  };

  const handleChange = (event) => {
    if (event) {
      const value = parseInt(event.target.value);
      const max = parseInt(event.target.max || 100);
      console.log(value)
      if (isNaN(value)) {
        event.target.value = event.target.checked ? 1 : 0;
      } else if (value < 0) {
        event.target.value = 0;
      } else if (value > max) {
        event.target.value = event.target.max;
      }
    }

    while (calculateTotal() > capacity_total) {
      event.target.value--;
    }

    resultElem.innerText = calculateTotal().toFixed(2);
  };

  additional_share_prices.forEach((share) => {
    const [key, price] = share.split(":");
    let input = document.querySelector(
      `[name$='${key}']`
    );
    
    if (!input) return;
    if (input.max) {
      input.max = Math.max(0, Math.floor(capacity_total / price));

      if (input.max == 0) {
        input.readOnly = true;
      }
    }
    input.addEventListener("change", handleChange);
  });

  handleChange();
};
