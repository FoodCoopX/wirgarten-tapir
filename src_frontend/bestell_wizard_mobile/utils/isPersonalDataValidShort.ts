import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { isPhoneNumberValid } from "../../bestell_wizard/utils/isPhoneNumberValid.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";

export function isPersonalDataValidShort(
  personalData: PersonalData,
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

  return isEmailValid(personalData.email);
}
