import { PersonalData } from "../types/PersonalData.ts";

export function getTestPersonalData(): PersonalData {
  const email =
    "max.mustermann" + Math.floor(Math.random() * 100000) + "@example.com";
  return {
    firstName: "Max",
    lastName: "Mustermann",
    email: email,
    emailConfirm: email,
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
