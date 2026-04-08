import { clearToken, getApiBase, getToken } from "./auth";

const DEFAULT_API_BASE = "http://127.0.0.1:8001";

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path: string, init: RequestInit = {}) {
  const apiBase = getApiBase() || (import.meta.env.VITE_API_BASE as string) || DEFAULT_API_BASE;
  const url = `${apiBase}/api/v1${path}`;
  const headers = { ...(init.headers || {}), ...authHeaders() };
  try {
    const res = await fetch(url, { ...init, headers });
    let data: any = {};
    try {
      data = await res.json();
    } catch (_e) {
      data = { code: res.status, message: "invalid_json_response", data: {} };
    }
    if (res.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    return data;
  } catch (e: any) {
    return {
      code: 0,
      message: e?.message || "network_error",
      data: {},
      detail: "Network request failed. Check backend URL/CORS/server status.",
    };
  }
}

export async function apiLogin(username: string, password: string) {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function apiRegister(payload: {
  username: string;
  email: string;
  password: string;
  hotel_name: string;
  hotel_location: { lat: number; lng: number };
}) {
  return request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function createCompetitor(name: string, externalId: string) {
  return request("/competitors", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      name,
      platform: "meituan",
      external_id: externalId,
      room_types: ["豪华大床房"],
    }),
  });
}

export async function listCompetitors() {
  return request("/competitors", { headers: authHeaders() });
}

export async function createActivity(title: string) {
  return request("/activities", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      title,
      start_time: "2026-05-01T09:00:00Z",
      end_time: "2026-05-03T18:00:00Z",
      source: "fairchina",
      activity_type: "exhibition",
      demand_level: "HIGH",
      demand_score: 0.9,
    }),
  });
}

export async function listActivities() {
  return request("/activities/calendar", { headers: authHeaders() });
}

export async function createAlertRule(name: string, threshold: number) {
  return request("/alert-rules", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, rule_type: "price_drop", threshold, is_active: true }),
  });
}

export async function listNotifications() {
  return request("/notifications", { headers: authHeaders() });
}

export async function listAlertRules() {
  return request("/alert-rules");
}

export async function dashboardOverview() {
  return request("/dashboard/overview");
}

export async function listWeeklyReports(page = 1, pageSize = 10) {
  return request(`/reports/weekly?page=${page}&page_size=${pageSize}`);
}

export async function generateWeeklyReport() {
  return request("/reports/weekly/generate", { method: "POST" });
}

export async function listExtensionDevices() {
  return request("/extension/devices");
}

export async function listExtensionReports(page = 1, pageSize = 20) {
  return request(`/extension/reports?page=${page}&page_size=${pageSize}`);
}

export async function listSystemUsers() {
  return request("/system/users");
}

export async function updateSystemUser(userId: string, role: string, isActive: boolean) {
  return request(`/system/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, is_active: isActive }),
  });
}

export async function listAuditLogs(page = 1, pageSize = 20) {
  return request(`/system/audit-logs?page=${page}&page_size=${pageSize}`);
}
