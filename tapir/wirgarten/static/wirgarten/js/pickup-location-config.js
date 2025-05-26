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
    PickupLocationMap.selectLocation(params.selected);

    for (const elem of locationRows) {
      if (elem.id === `row-${params.selected}`) {
        elem.style.background = "var(--active-color)";
        elem.scrollIntoView();
      } else {
        elem.style.background = "";
      }
    }

    deleteButton.disabled = !canDelete[params.selected];
    editButton.disabled = false;
  }
};

const handleEdit = () => {
  url = `/wirgarten/admin/pickuplocations/edit/${Tapir.getUrlParams().selected}`;
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
        window.location.href = `/wirgarten/admin/pickuplocations/delete/${id}`;
      }
    },
  );
};
