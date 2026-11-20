export function interpolate(
  format: string,
  args: Record<string, unknown>,
): string {
  return format.replace(/\{(\w+)\}/g, (_, key) => {
    const value = args[key];
    if (value === null || value === undefined) {
      return "";
    }
    return typeof value === "object" ? JSON.stringify(value) : String(value);
  });
}
