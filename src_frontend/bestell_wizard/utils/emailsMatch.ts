export function emailsMatch(email: string, emailConfirm: string): boolean {
  return email.trim() === emailConfirm.trim();
}

export function shouldShowEmailMismatchWarning(
  email: string,
  emailConfirm: string,
): boolean {
  const trimmedEmail = email.trim();
  const trimmedConfirm = emailConfirm.trim();
  return (
    trimmedConfirm.length >= trimmedEmail.length &&
    trimmedConfirm.length > 0 &&
    trimmedConfirm !== trimmedEmail
  );
}
