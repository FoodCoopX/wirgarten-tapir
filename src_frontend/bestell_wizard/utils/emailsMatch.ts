export function emailsMatch(email: string, emailConfirm: string): boolean {
  return email.trim() === emailConfirm.trim();
}

export function shouldShowEmailMismatchWarning(
  email: string,
  emailConfirm: string,
): boolean {
  return emailConfirm.trim().length > 0 && !emailsMatch(email, emailConfirm);
}
