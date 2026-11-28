export function formatPercentage(value: number): string {
  return value.toLocaleString("de-DE", {
    style: "percent",
    maximumFractionDigits: 2,
  });
}
