export function replaceTokens(baseString: string, firstName: string) {
  return baseString.replace("{vorname}", firstName);
}
