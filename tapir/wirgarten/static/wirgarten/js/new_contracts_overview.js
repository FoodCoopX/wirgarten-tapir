const getChecked = () => {
  const checkboxes = document.querySelectorAll(`[id^="tr-"]`)
  const checkedCheckboxes = Array.from(checkboxes).filter(checkbox => checkbox.classList.contains('active'))

  if (checkedCheckboxes.length < 1) {
    document.getElementById('confirmBtn').disabled = 'disabled';
    return;
  } else {
    document.getElementById('confirmBtn').disabled = false;
  }

  const regex = /^tr-(.+)-(.{10})$/;

  return Array.from(checkedCheckboxes).reduce((acc, checkbox) => {
     const match = checkbox.id.match(regex);

    // If the regex doesn't match the ID, skip this checkbox
    if (!match) {
      console.warn(`ID "${checkbox.id}" does not match the expected format.`);
      return acc;
    }

    const [, type, id] = match;

    if (acc[type]) {
      acc[type].push(id);
    } else {
      acc[type] = [id];
    }

    return acc;
  }, {});
}

const handleCheckButton = () => {
    const checkedCheckboxes = getChecked();

    const count = Object.entries(checkedCheckboxes).reduce((acc, [type, ids]) => {
        acc += ids.length;
        return acc;
    }, 0);

    ConfirmationModal.open('Bist du dir sicher?', `Möchtest du die <strong>${count}</strong> ausgewählten Zeichnungen auf <strong>geprüft</strong> setzen?`, 'Ja, auf geprüft setzen', 'danger', () => {
        window.location.href='/wirgarten/admin/newcontracts/confirm' + Tapir.stringifyUrlParams(checkedCheckboxes);
    });
}

const handleCheckbox = (type, contractId, check=undefined) => {
    const checkbox = document.getElementById('input-' + type + '-' + contractId);

    if (check !== undefined) {
        checkbox.checked = check;
    } else {
        checkbox.checked =  !checkbox.checked;
    }

    const tr = document.getElementById('tr-' + type + '-' + contractId);
    checkbox.checked ? tr.classList.add('active') : tr.classList.remove('active');

    const selectedBadge = document.getElementById(type + '-selected-badge');
    const checked = getChecked();
    if(checked && checked[type]){
        selectedBadge.style.display='inline';
        selectedBadge.innerText=checked[type].length;
    } else {
        selectedBadge.style.display='none';
        selectedBadge.innerText='';
    }
}

const handleAllCheckboxes = (type, checked) => {
    const checkboxes = document.querySelectorAll('.input-' + type);
    checkboxes.forEach(checkbox => {
        handleCheckbox(type, checkbox.id.slice(-10), checked);
    });
}

const handleKeyDown = (event) => {
  if (event.ctrlKey && event.key === 'a') {
    event.preventDefault();

    const tab = document.querySelector('button.nav-link.active')
    type = tab.id.slice(0, -4);

    const selectAllCheckbox = document.getElementById('checkall-' + type)
    selectAllCheckbox.checked = !selectAllCheckbox.checked

    handleAllCheckboxes(type, selectAllCheckbox.checked);
  }
}

document.addEventListener('keydown', handleKeyDown);