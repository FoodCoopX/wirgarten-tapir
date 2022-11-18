 const handleRowClick = (id) => {
        Tapir.replaceUrlParams({selected: id});
        initSelected();
}

const locationRows = document.getElementsByClassName("location-row");
const initSelected = () => {
    const params = Tapir.getUrlParams();
    if(params.selected){
        PickupLocationMap.selectLocation(params.selected);

        for (const elem of locationRows) {
            if(elem.id === `row-${params.selected}`){
                elem.style.background='var(--active-color)';
                elem.scrollIntoView();
            } else {
                elem.style.background='';
            }
        }

        document.getElementById("delete-location").disabled=!canDelete[params.selected]
    }
}

const handleEdit = () => {
    url = `/wirgarten/admin/pickuplocations/edit/${Tapir.getUrlParams().selected}`
    FormModal.load(url, "Abholort ändern")
}

const handleDelete = () => {
      const id = Tapir.getUrlParams().selected;
      if(canDelete[id]){
        window.location.href =  `/wirgarten/admin/pickuplocations/delete/${id}`
      }
}