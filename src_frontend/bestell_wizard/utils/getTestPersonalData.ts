import { PersonalData } from "../types/PersonalData.ts";

export function getTestPersonalData(): PersonalData {
  return {
    firstName: "Max",
    lastName: "Mustermann",
    email: "max.mustermann@example.com",
    phoneNumber: "01234567890",
    street: "Musterstrasse 1",
    street2: "",
    postCode: "12345",
    city: "Musterstadt",
    country: "DE",
    account_owner: "Max Mustermann",
    birthdate: new Date("1990-12-22"),
    iban: "DE89370400440532013000",
  };
}
