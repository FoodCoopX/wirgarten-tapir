export function formatPercentage(value: number): string {
  return (value * 100).toFixed(2) + "\u00A0%";
}
