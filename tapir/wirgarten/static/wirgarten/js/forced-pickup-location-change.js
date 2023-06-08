const pickupLocationElem = document.getElementById('pickup_location');
const changeDateElem = document.getElementById('pickup_location_change_date');

let hasError = false;
if (pickupLocationElem){
    hasError = pickupLocationElem.querySelector('.invalid-feedback') || false;
    if(!hasError){
        pickupLocationElem.style.display = 'none';
    }
}
if(changeDateElem && !hasError){
    changeDateElem.style.display = 'none';
}