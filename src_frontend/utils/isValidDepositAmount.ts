export function isValidDepositAmount(
  amount: number,
  minimum: number,
  increment: number,
): boolean {
  const cents = Math.round(amount * 100);
  const minimumCents = Math.round(minimum * 100);
  const incrementCents = Math.round(increment * 100);
  return (
    Number.isFinite(amount) &&
    Math.abs(amount * 100 - cents) < 0.000001 &&
    cents >= minimumCents &&
    cents <= 99999999 &&
    incrementCents > 0 &&
    (cents - minimumCents) % incrementCents === 0
  );
}
