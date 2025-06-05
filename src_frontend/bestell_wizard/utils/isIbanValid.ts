import IBAN from "iban";

export function isIbanValid(iban: string): boolean {
  return IBAN.isValid(iban);
}
