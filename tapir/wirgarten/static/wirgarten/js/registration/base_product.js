let soliElem = document.getElementsByName("solidarity_price_harvest_shares")[0];
if (!soliElem) {
  soliElem = document.getElementsByName(
    "base_product-solidarity_price_harvest_shares",
  )[0];
}
const origOptions = [...soliElem.options];

const calculatePrice = (harvest_share) => {
  const [key, price] = harvest_share.split(":");
  let elem = document.getElementsByName("base_product-" + key)[0];
  if (!elem) {
    elem = document.getElementsByName(key)[0];
  }
  if (!elem) {
    return 0;
  }
  return elem.value * price;
};

var initHarvestShareSummary = (harvest_share_prices, solidarity_total) => {
  const resultElem = document.getElementById("harvest_shares_total");
  let customSoliElem = document.getElementById(
    "id_solidarity_price_absolute_harvest_shares",
  );
  if (!customSoliElem) {
    customSoliElem = document.getElementById(
      "id_base_product-solidarity_price_absolute_harvest_shares",
    );
  }

  for (const elementNameToPricePair of harvest_share_prices.split(",")) {
    const [elementName, price] = elementNameToPricePair.split(":");
    document.getElementsByName(elementName)[0].nextSibling.innerText = price + " € inkl. MwSt / Monat";
  }

  const calculateTotalWithoutSoliPrice = () =>
    harvest_share_prices
      .split(",")
      .map(calculatePrice)
      .reduce((a, b) => a + b);
  const calculateTotal = () => {
    if (soliElem.value === "custom") {
      return (
        calculateTotalWithoutSoliPrice() + parseFloat(customSoliElem.value)
      );
    } else {
      return (
        calculateTotalWithoutSoliPrice() * (1 + parseFloat(soliElem.value))
      );
    }
  };
  const warningCannotReduceElem = document.getElementById(
    "warning-cannot-reduce",
  );
  let totalWithoutSoli = calculateTotalWithoutSoliPrice();
  const initDependentFields = () => {
    resultElem.innerText = calculateTotal().toFixed(2);
    totalWithoutSoli = calculateTotalWithoutSoliPrice();
    if (soliElem.value === "custom") {
      customSoliElem.disabled = false;
      customSoliElem.required = true;
    } else {
      customSoliElem.disabled = true;
      customSoliElem.value = (totalWithoutSoli * soliElem.value).toFixed(2);
    }

    filterSoliPriceOptions(totalWithoutSoli, solidarity_total);
  };

  const handleChange = (event, max_shares) => {
    if (event && event.target && max_shares) {
      if (event.target.value < 0) {
        event.target.value = 0;
      } else if (event.target.value > max_shares) {
        event.target.value = max_shares;
      }
    }

    initDependentFields();

    const submitBtn = document.getElementById("submit-btn");
    if (warningCannotReduceElem && totalWithoutSoli < originalTotal) {
      if (submitBtn) {
        submitBtn.disabled = true;
      }
      warningCannotReduceElem.style.display = "block";
    } else {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
      if (warningCannotReduceElem)
        warningCannotReduceElem.style.display = "none";
    }
  };

  customSoliElem.addEventListener("change", (e) => {
    if (e.target.value === 0 || isNaN(e.target.value)) {
      e.target.value = 0;
    }

    if (e.target.value < 0) {
      e.target.value = 0;
    }

    e.target.value = parseFloat(e.target.value).toFixed(2);

    handleChange(e);
  });

  const filterSoliPriceOptions = (shares_total, solidarity_total) => {
    const selected = soliElem.value;

    options = [...origOptions].filter((o) => {
      if (o.value === "custom") {
        return true;
      }

      const value = parseFloat(o.value);
      return value >= 0 || -value * shares_total < solidarity_total;
    });

    while (soliElem.firstChild) {
      soliElem.removeChild(soliElem.firstChild);
    }

    const newSelectEl = soliElem.cloneNode(true);

    for (const option of options) {
      newSelectEl.appendChild(option);
    }

    soliElem.parentNode.replaceChild(newSelectEl, soliElem);
    soliElem = newSelectEl;

    const optArr = Array.from(options);
    soliElem.value = optArr.some((o) => o.value === selected)
      ? selected
      : optArr[optArr.length - 1].value;

    resultElem.innerText = calculateTotal().toFixed(2);
    soliElem.addEventListener("change", (e) => {
      // if the value is 'custom', we set the value of the custom input to the price without solidarity + at least 10€ + difference to get a round sum (10)
      if (e.target.value === "custom") {
        const priceWithoutSoli = calculateTotalWithoutSoliPrice();
        customSoliElem.value = (
          priceWithoutSoli +
          20 -
          (priceWithoutSoli % 10) -
          priceWithoutSoli
        ).toFixed(2);
      }

      handleChange(e);
    });
  };

  harvest_share_prices.split(",").forEach((harvest_share) => {
    const [key, price] = harvest_share.split(":");
    let input = document.getElementsByName("base_product-" + key)[0];
    if (!input) {
      input = document.getElementsByName(key)[0];
    }
    const clone = input.cloneNode(true);

    // Replace the original element with its clone to remove old event listeners
    input.parentNode.replaceChild(clone, input);
    input = clone;

    input.addEventListener("change", (e) => handleChange(e, 10));
    input.min = 0;
    input.max = 10;
  });

  resultElem.innerText = calculateTotal().toFixed(2);

  initDependentFields();
};
