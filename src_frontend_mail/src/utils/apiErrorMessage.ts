const MAX_ERROR_LENGTH = 300;

const flattenMessages = (data: unknown): string[] => {
  if (typeof data === "string") return [data];
  if (!data || typeof data !== "object") return [];

  return Object.values(data as Record<string, unknown>)
    .flatMap((value) => (Array.isArray(value) ? value : [value]))
    .filter((value): value is string => typeof value === "string");
};

export const getApiErrorMessage = async (
  error: unknown,
  fallback: string,
): Promise<string> => {
  const response = (error as { response?: Response } | null)?.response;
  if (!response) return fallback;

  try {
    const text = (await response.text()).trim();
    if (!text || text.startsWith("<")) return fallback;

    try {
      const messages = flattenMessages(JSON.parse(text));
      return messages.length > 0 ? messages.join(" ") : fallback;
    } catch {
      return text.length > MAX_ERROR_LENGTH
        ? `${text.slice(0, MAX_ERROR_LENGTH)}…`
        : text;
    }
  } catch {
    return fallback;
  }
};
