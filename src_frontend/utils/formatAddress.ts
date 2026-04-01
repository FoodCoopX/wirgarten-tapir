export default function formatAddress(
  street: string,
  street2: string | undefined,
  postcode: string,
  city: string,
) {
  let result = street;
  if (street2) result += ", " + street2;
  result += ", " + postcode + " " + city;
  return result;
}
