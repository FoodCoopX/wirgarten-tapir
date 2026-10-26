/**
 * Replaces the canonical term "Beitragsrunde" in user-facing texts with the
 * configured display name. Idempotent: a display name that does not contain
 * "Beitragsrunde" is not replaced again.
 */
export function applyDisplayName(text: string, displayName?: string): string {
  if (!text || !displayName || displayName === "Beitragsrunde") {
    return text;
  }
  return text.split("Beitragsrunde").join(displayName);
}
