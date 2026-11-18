export function getPickupLocationLatLng(pickupLocation: {
  latitude?: string | null;
  longitude?: string | null;
}): [number, number] | null {
  if (pickupLocation.latitude == null || pickupLocation.longitude == null) {
    return null;
  }
  return [
    Number.parseFloat(pickupLocation.latitude),
    Number.parseFloat(pickupLocation.longitude),
  ];
}
