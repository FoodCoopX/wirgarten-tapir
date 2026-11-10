export function getBiddingRoundLoginUrl(): string {
  const next = `${window.location.pathname}?skip_intro=1`;
  return `/accounts/login/?next=${encodeURIComponent(next)}`;
}
