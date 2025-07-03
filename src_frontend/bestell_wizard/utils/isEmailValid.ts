import * as EmailValidator from "email-validator";

export function isEmailValid(email: string): boolean {
  return EmailValidator.validate(email);
}
