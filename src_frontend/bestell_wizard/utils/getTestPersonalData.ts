import { PersonalData } from "../types/PersonalData.ts";

export function getTestPersonalData(): PersonalData {
  return {
    firstName: "Max",
    lastName: "Mustermann",
    email: "max.mustermann@example.com",
    phoneNumber: "017626274538",
    street: "Musterstrasse 1",
    street2: "",
    postcode: "12345",
    city: "Musterstadt",
    country: "DE",
    accountOwner: "Max Mustermann",
    birthdate: new Date("1990-12-22"),
    iban: "DE89370400440532013000",
    paymentRhythm: "monthly",
  };
}
