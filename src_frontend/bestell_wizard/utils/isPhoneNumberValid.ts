import { isValidPhoneNumber } from "libphonenumber-js";

export function isPhoneNumberValid(phoneNumber: string) {
  return isValidPhoneNumber(phoneNumber, "DE");
}
