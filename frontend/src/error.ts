export function normalizeError(data: unknown): string {
  if (!data || typeof data !== "object") return "Unknown error";
  const obj = data as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  if (typeof obj.message === "string") return obj.message;
  return "Request failed";
}
