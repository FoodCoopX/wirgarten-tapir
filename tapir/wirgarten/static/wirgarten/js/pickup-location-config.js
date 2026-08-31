const handleRowClick = (id) => {
  Tapir.replaceUrlParams({ selected: id });
  initSelected();
};

const initSelected = () => {
  const deleteButton = document.getElementById("delete-location");
  const editButton = document.getElementById("edit-location");
  const locationRows = document.getElementsByClassName("location-row");

  const params = Tapir.getUrlParams();
  if (params.selected) {
    let found = false;
    for (const elem of locationRows) {
      if (elem.id === `row-${params.selected}`) {
        elem.classList.add("table-active");
        elem.scrollIntoView();
        found = true;
      } else {
        elem.classList.remove("table-active");
      }
    }

    if (!found) {
      // The filter (or pagination) hid the previously-selected row.
      // Clear the selection so a stale id doesn't enable action buttons
      // pointing at a row the user can no longer see.
      delete params.selected;
      Tapir.replaceUrlParams(params);
      deleteButton.disabled = true;
      editButton.disabled = true;
      return;
    }

    if (typeof PickupLocationMap !== "undefined" && PickupLocationMap.selectLocation) {
      PickupLocationMap.selectLocation(params.selected);
    }
    deleteButton.disabled = !canDelete[params.selected];
    editButton.disabled = false;
  } else {
    deleteButton.disabled = true;
    editButton.disabled = true;
  }
};

const handleEdit = () => {
  url = `/tapir/admin/pickuplocations/edit/${Tapir.getUrlParams().selected}`;
  FormModal.load(url, "Abholort bearbeiten");
};

const handleDelete = () => {
  ConfirmationModal.open(
    "Bist du dir sicher?",
    "Möchtest du diesen Abholort wirklich löschen?",
    "Löschen",
    "danger",
    () => {
      const id = Tapir.getUrlParams().selected;
      if (canDelete[id]) {
        window.location.href = `/tapir/admin/pickuplocations/delete/${id}`;
      }
    },
  );
};
