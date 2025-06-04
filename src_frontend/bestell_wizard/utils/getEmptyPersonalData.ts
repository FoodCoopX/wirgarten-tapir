import { PersonalData } from "../types/PersonalData.ts";

export function getEmptyPersonalData(): PersonalData {
  return {
    firstName: "",
    lastName: "",
    email: "",
    phoneNumber: "",
    street: "",
    street2: "",
    postCode: "",
    city: "",
    country: "DE",
    birthdate: new Date(),
    account_owner: "",
    iban: "",
  };
}
