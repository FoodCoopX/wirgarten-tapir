import { PersonalData } from "../../bestell_wizard/types/PersonalData.ts";
import { emailsMatch } from "../../bestell_wizard/utils/emailsMatch.ts";
import { isEmailValid } from "../../bestell_wizard/utils/isEmailValid.ts";
import { isPhoneNumberValid } from "../../bestell_wizard/utils/isPhoneNumberValid.ts";

export function isPersonalDataValidShort(
  personalData: PersonalData,
  emailAddressAlreadyInUse: boolean,
): boolean {
  if (emailAddressAlreadyInUse) return false;
  if (!personalData.firstName) return false;
  if (!personalData.lastName) return false;
  if (!personalData.email) return false;
  if (!emailsMatch(personalData.email, personalData.emailConfirm)) return false;
  if (!personalData.street) return false;
  if (!personalData.postcode) return false;
  if (!personalData.city) return false;
  if (!personalData.country) return false;

  if (personalData.phoneNumber && !isPhoneNumberValid(personalData.phoneNumber)) {
    return false;
  }

  return isEmailValid(personalData.email);
}
