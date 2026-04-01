import { PersonalData } from "../types/PersonalData.ts";

export function getTestPersonalData(): PersonalData {
  return {
    firstName: "Max",
    lastName: "Mustermann",
    email:
      "max.mustermann" + Math.floor(Math.random() * 100000) + "@example.com",
    phoneNumber: "017626274538",
    street: "Musterstrasse 1",
    street2: "",
    postcode: "12345",
    city: "Musterstadt",
    country: "DE",
    accountOwner: "Max Mustermann",
    iban: "DE89370400440532013000",
    paymentRhythm: "monthly",
  };
}
