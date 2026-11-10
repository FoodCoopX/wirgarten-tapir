const handleRowClick = (id) => {
  Tapir.replaceUrlParams({ selected: id });
  initSelected();
};

const initSelected = () => {
  const locationRows = document.getElementsByClassName("location-row");

  const params = Tapir.getUrlParams();
  if (!params.selected) {
    return;
  }

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
    // Clear the selection so a stale id doesn't make the action buttons
    // target a row the user can no longer see.
    delete params.selected;
    Tapir.replaceUrlParams(params);
    return;
  }

  if (
    typeof PickupLocationMap !== "undefined" &&
    PickupLocationMap.selectLocation
  ) {
    PickupLocationMap.selectLocation(params.selected);
  }
};
