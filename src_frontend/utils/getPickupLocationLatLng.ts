export function getPickupLocationLatLng(pickupLocation: {
  coordsLat?: string | null;
  coordsLon?: string | null;
}): [number, number] | null {
  if (pickupLocation.coordsLat == null || pickupLocation.coordsLon == null) {
    return null;
  }
  // coords_lon holds the latitude and coords_lat the longitude everywhere in Tapir
  return [
    Number.parseFloat(pickupLocation.coordsLon),
    Number.parseFloat(pickupLocation.coordsLat),
  ];
}
