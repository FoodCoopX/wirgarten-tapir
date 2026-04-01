import { PersonalData } from "../types/PersonalData.ts";
import { isIbanValid } from "./isIbanValid.ts";
import { isEmailValid } from "./isEmailValid.ts";
import { isPhoneNumberValid } from "./isPhoneNumberValid.ts";

export function isPersonalDataValid(
  personalData: PersonalData,
  waitingListModeEnabled: boolean,
  emailAddressAlreadyInUse: boolean,
): boolean {
  if (emailAddressAlreadyInUse) return false;
  if (!personalData.firstName) return false;
  if (!personalData.lastName) return false;
  if (!personalData.email) return false;
  if (!personalData.phoneNumber) return false;
  if (!personalData.street) return false;
  if (!personalData.postcode) return false;
  if (!personalData.city) return false;
  if (!personalData.country) return false;

  if (!isPhoneNumberValid(personalData.phoneNumber)) {
    return false;
  }

  if (!isEmailValid(personalData.email)) {
    return false;
  }

  if (!waitingListModeEnabled) {
    if (!personalData.accountOwner) return false;
    if (!personalData.iban) return false;
    if (!isIbanValid(personalData.iban)) return false;
  }

  return true;
}
