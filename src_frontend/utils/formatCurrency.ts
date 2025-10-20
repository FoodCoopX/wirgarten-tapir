export function formatCurrency(value: number): string {
  return value.toFixed(2) + "\u00A0€";
}
