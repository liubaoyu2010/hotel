const TOKEN_KEY = "token";
const API_BASE_KEY = "api_base";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function getApiBase(): string {
  return localStorage.getItem(API_BASE_KEY) ?? "";
}

export function setApiBase(base: string): void {
  localStorage.setItem(API_BASE_KEY, base);
}

export function getUserRole(): string {
  const token = getToken();
  if (!token) return "";
  const parts = token.split(".");
  if (parts.length < 2) return "";
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return String(payload.role || "");
  } catch (_e) {
    return "";
  }
}
