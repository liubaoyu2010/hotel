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

// Auth
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

// Competitors
export async function createCompetitor(name: string, externalId: string, roomTypes: string[] = ["豪华大床房"]) {
  return request("/competitors", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, platform: "meituan", external_id: externalId, room_types: roomTypes }),
  });
}

export async function listCompetitors() {
  return request("/competitors");
}

export async function getCompetitorPriceHistory(competitorId: string, startTime?: string, endTime?: string) {
  const params = new URLSearchParams();
  if (startTime) params.set("start_time", startTime);
  if (endTime) params.set("end_time", endTime);
  const qs = params.toString();
  return request(`/competitors/${competitorId}/price-history${qs ? "?" + qs : ""}`);
}

export async function updateCompetitor(competitorId: string, payload: { name?: string; external_id?: string; room_types?: string[]; is_active?: boolean }) {
  return request(`/competitors/${competitorId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
}

export async function deleteCompetitor(competitorId: string) {
  return request(`/competitors/${competitorId}`, { method: "DELETE" });
}

// Profile
export async function getProfile() {
  return request("/profile");
}

export async function updateProfile(payload: { hotel_name?: string; hotel_lat?: number; hotel_lng?: number; email?: string }) {
  return request("/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
}

// Competitor Aliases
export async function listCompetitorAliases() {
  return request("/competitor-aliases");
}

export async function upsertCompetitorAliases(aliasMap: Record<string, string>) {
  return request("/competitor-aliases", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ alias_map: aliasMap }),
  });
}

// Activities
export async function createActivity(payload: any) {
  return request("/activities", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
}

export async function deleteActivity(activityId: string) {
  return request(`/activities/${activityId}`, { method: "DELETE" });
}

export async function listActivities(startDate?: string, endDate?: string) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return request(`/activities/calendar${qs ? "?" + qs : ""}`);
}

export async function listNearbyActivities(radiusKm: number = 3.0) {
  return request(`/activities/nearby?radius_km=${radiusKm}`);
}

export async function geocodeAddress(address: string, city?: string) {
  const params = new URLSearchParams({ address });
  if (city) params.set("city", city);
  return request(`/utils/geocode?${params.toString()}`);
}

export async function triggerActivityCollect(payload: { city?: string; radius_km?: number; collector_name?: string } = {}) {
  return request("/activities/collect", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
}

export async function listActivityCollectors() {
  return request("/activities/collectors");
}

// Alerts
export async function createAlertRule(name: string, threshold: number, ruleType: string = "price_drop") {
  return request("/alert-rules", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, rule_type: ruleType, threshold, is_active: true }),
  });
}

export async function listAlertRules() {
  return request("/alert-rules");
}

export async function updateAlertRule(ruleId: string, payload: { name?: string; threshold?: number; is_active?: boolean }) {
  return request(`/alert-rules/${ruleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
}

export async function deleteAlertRule(ruleId: string) {
  return request(`/alert-rules/${ruleId}`, { method: "DELETE" });
}

export async function listAlertRecords() {
  return request("/alerts");
}

// Notifications
export async function listNotifications(page = 1, pageSize = 20) {
  return request(`/notifications?page=${page}&page_size=${pageSize}`);
}

// Dashboard
export async function dashboardOverview(days = 7) {
  return request(`/dashboard/overview?days=${days}`);
}

// Reports
export async function listWeeklyReports(page = 1, pageSize = 10) {
  return request(`/reports/weekly?page=${page}&page_size=${pageSize}`);
}

export async function generateWeeklyReport() {
  return request("/reports/weekly/generate", { method: "POST" });
}

// Extension
export async function listExtensionDevices() {
  return request("/extension/devices");
}

export async function listExtensionReports(page = 1, pageSize = 20) {
  return request(`/extension/reports?page=${page}&page_size=${pageSize}`);
}

// System
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
