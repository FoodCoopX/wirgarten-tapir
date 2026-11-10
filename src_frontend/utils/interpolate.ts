export function interpolate(
  format: string,
  args: Record<string, unknown>,
  // Kept for signature compatibility; only used for `{name}` placeholders.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  named = true,
): string {
  return format.replace(/\{(\w+)\}/g, (_, key) => String(args[key] ?? ""));
}
