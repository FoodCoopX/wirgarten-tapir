import { PersonalData } from "../types/PersonalData.ts";

export function getEmptyPersonalData(): PersonalData {
  return {
    firstName: "",
    lastName: "",
    email: "",
    phoneNumber: "",
    street: "",
    street2: "",
    postcode: "",
    city: "",
    country: "DE",
    birthdate: new Date(),
    accountOwner: "",
    iban: "",
    paymentRhythm: "monthly",
  };
}
