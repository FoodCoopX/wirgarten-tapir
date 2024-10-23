const initSummary = (min_shares, share_price) => {
  const resultElem = document.getElementById("cooperative_shares_total");
  let input = document.getElementsByName("coop_shares-cooperative_shares")[0];
  if (!input) {
    input = document.getElementsByName("cooperative_shares")[0];
  }
  input.step = 50;
  input.min = 0; //input.value = min_shares * share_price;

  input.addEventListener("change", (event) => {
    if (event.target.value < input.min) {
      input.value = input.min;
    }
  });

  const handleChange = (evt) => {
    const value = evt.target.value;
    const diff = value % 50;
    if (diff > 0) {
      const fallback = diff > 24 ? Number(value) + (50 - diff) : value - diff;
      input.value = Math.max(fallback, input.min);
    }

    resultElem.innerText = input.value;
  };

  resultElem.innerText = input.value;
  input.addEventListener("change", handleChange);
};

function initStudentCheckboxEvents() {
  const studentCheckbox = document.getElementById("id_coop_shares-is_student");
  const sharesInput = document.getElementById(
    "id_coop_shares-cooperative_shares",
  );
  const consentCheckbox = document.getElementById(
    "id_coop_shares-statute_consent",
  );

  if (!studentCheckbox) {
    return;
  }

  function updateFieldsEnabledDependingOnStudentStatus() {
    sharesInput.disabled = studentCheckbox.checked;
    consentCheckbox.disabled = studentCheckbox.checked;
    if (studentCheckbox) {
      sharesInput.value = 0;
      consentCheckbox.checked = false;
    }
  }

  studentCheckbox.addEventListener("change", (event) => {
    updateFieldsEnabledDependingOnStudentStatus();
  });

  updateFieldsEnabledDependingOnStudentStatus();
}

document.addEventListener("DOMContentLoaded", initStudentCheckboxEvents);
