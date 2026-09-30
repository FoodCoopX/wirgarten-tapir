import { PersonalData } from "../types/PersonalData.ts";

export function getEmptyPersonalData(): PersonalData {
  return {
    firstName: "",
    lastName: "",
    email: "",
    emailConfirm: "",
    phoneNumber: "",
    street: "",
    street2: "",
    postcode: "",
    city: "",
    country: "DE",
    accountOwner: "",
    iban: "",
    paymentRhythm: "monthly",
  };
}
