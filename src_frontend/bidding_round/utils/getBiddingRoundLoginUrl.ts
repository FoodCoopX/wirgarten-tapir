export function getBiddingRoundLoginUrl(): string {
  const next = window.location.pathname;
  return `/accounts/login/?next=${encodeURIComponent(next)}`;
}
