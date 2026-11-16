export function interpolate(
  format: string,
  args: Record<string, unknown>,
): string {
  return format.replace(/\{(\w+)\}/g, (_, key) => String(args[key] ?? ""));
}
