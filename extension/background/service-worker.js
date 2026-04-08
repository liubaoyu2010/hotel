chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    apiBase: "http://127.0.0.1:8001",
    deviceId: crypto.randomUUID(),
    reportRetryQueue: [],
    autoCollectEnabled: true,
    minCollectIntervalMs: 120000,
    lastCollectAtMs: 0,
    lastAutoReport: null,
    lastPayloadFingerprint: "",
    lastPayloadAtMs: 0,
    dedupWindowMs: 120000,
    competitorAliasMap: {},
    aliasChangeHistory: [],
    autoReportHistory: [],
    lastUnmatchedCompetitors: [],
  });
  chrome.alarms.create("retry-report-queue", { periodInMinutes: 1 });
});

function normalizeName(name) {
  return String(name || "").trim().toLowerCase();
}

function payloadFingerprint(payload) {
  const competitors = (payload?.data?.competitors || [])
    .map((x) => ({
      name: String(x.name || "").trim(),
      room_type: String(x.room_type || "").trim(),
      price: Number(x.price || 0),
    }))
    .sort((a, b) =>
      `${a.name}|${a.room_type}|${a.price}`.localeCompare(`${b.name}|${b.room_type}|${b.price}`)
    );
  const core = {
    type: payload?.type || "",
    source: payload?.source || "",
    url: payload?.url || "",
    competitors,
  };
  return JSON.stringify(core);
}

async function appendAutoReportHistory(item) {
  const state = await chrome.storage.local.get(["autoReportHistory"]);
  const history = Array.isArray(state.autoReportHistory) ? state.autoReportHistory : [];
  history.unshift(item);
  await chrome.storage.local.set({ autoReportHistory: history.slice(0, 10) });
}

async function applyAliasMapToPayload(payload) {
  const state = await chrome.storage.local.get(["competitorAliasMap"]);
  const aliasMap = state.competitorAliasMap || {};
  const comps = payload?.data?.competitors || [];
  for (const c of comps) {
    const key = normalizeName(c.name);
    if (key && aliasMap[key]) c.name = aliasMap[key];
  }
  return payload;
}

async function enqueueFailedReport(payload) {
  const state = await chrome.storage.local.get(["reportRetryQueue"]);
  const queue = Array.isArray(state.reportRetryQueue) ? state.reportRetryQueue : [];
  queue.push({
    payload,
    createdAt: new Date().toISOString(),
    retryCount: 0,
  });
  await chrome.storage.local.set({ reportRetryQueue: queue });
}

async function sendReport(payload) {
  const state = await chrome.storage.local.get(["apiBase", "extensionToken"]);
  if (!state.apiBase || !state.extensionToken) {
    throw new Error("Missing apiBase or extensionToken");
  }
  const res = await fetch(`${state.apiBase}/api/v1/extension/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Extension-Token": state.extensionToken,
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    const msg = data?.message || `HTTP ${res.status}`;
    throw new Error(`Report failed: ${msg}`);
  }
  return data;
}

async function updateLastAutoReport(partial) {
  const now = new Date().toISOString();
  await chrome.storage.local.set({
    lastAutoReport: {
      time: now,
      ...partial,
    },
  });
  await appendAutoReportHistory({
    time: now,
    ...partial,
  });
}

async function retryQueuedReports() {
  const state = await chrome.storage.local.get(["reportRetryQueue"]);
  const queue = Array.isArray(state.reportRetryQueue) ? state.reportRetryQueue : [];
  if (!queue.length) return;

  const remain = [];
  for (const item of queue) {
    try {
      await sendReport(item.payload);
    } catch (_err) {
      const nextCount = Number(item.retryCount || 0) + 1;
      if (nextCount < 10) {
        remain.push({ ...item, retryCount: nextCount });
      }
    }
  }
  await chrome.storage.local.set({ reportRetryQueue: remain });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "retry-report-queue") {
    retryQueuedReports();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "PING") {
    sendResponse({ ok: true, source: "service-worker" });
    return;
  }

  if (message?.type === "REPORT_PAYLOAD") {
    let payload = message.payload;
    chrome.storage.local.set({ lastCollectAtMs: Date.now() });
    applyAliasMapToPayload(payload).then(async (mappedPayload) => {
      payload = mappedPayload;
      const state = await chrome.storage.local.get([
        "lastPayloadFingerprint",
        "lastPayloadAtMs",
        "dedupWindowMs",
        "reportRetryQueue",
      ]);
      const fp = payloadFingerprint(payload);
      const dedupWindowMs = Number(state.dedupWindowMs || 120000);
      const lastFp = String(state.lastPayloadFingerprint || "");
      const lastAt = Number(state.lastPayloadAtMs || 0);
      const now = Date.now();

      if (fp === lastFp && now - lastAt < dedupWindowMs) {
        await updateLastAutoReport({
          ok: true,
          mode: "auto",
          processedCount: 0,
          queueSize: (state.reportRetryQueue || []).length || 0,
          dedupSkipped: true,
          error: "",
        });
        sendResponse({ ok: true, dedupSkipped: true });
        return;
      }

      await chrome.storage.local.set({
        lastPayloadFingerprint: fp,
        lastPayloadAtMs: now,
      });

      sendReport(payload)
      .then(async (data) => {
        const unmatched = data?.data?.unmatched_competitors || [];
        await chrome.storage.local.set({ lastUnmatchedCompetitors: unmatched });
        await updateLastAutoReport({
          ok: true,
          mode: "auto",
          processedCount: data?.data?.processed_count ?? 0,
          queueSize: (await chrome.storage.local.get(["reportRetryQueue"])).reportRetryQueue?.length || 0,
          dedupSkipped: false,
          unmatchedCount: unmatched.length,
          error: "",
        });
        sendResponse({ ok: true, data });
      })
      .catch(async (err) => {
        await enqueueFailedReport(payload);
        const q = await chrome.storage.local.get(["reportRetryQueue"]);
        const size = Array.isArray(q.reportRetryQueue) ? q.reportRetryQueue.length : 0;
        await updateLastAutoReport({
          ok: false,
          mode: "auto",
          processedCount: 0,
          queueSize: size,
          dedupSkipped: false,
          unmatchedCount: 0,
          error: String(err),
        });
        sendResponse({ ok: false, error: String(err) });
      });
    });
    return true;
  }

  if (message?.type === "QUEUE_STATUS") {
    chrome.storage.local.get(["reportRetryQueue"]).then((state) => {
      const queue = Array.isArray(state.reportRetryQueue) ? state.reportRetryQueue : [];
      sendResponse({ ok: true, queueSize: queue.length });
    });
    return true;
  }

  if (message?.type === "FORCE_RETRY_QUEUE") {
    retryQueuedReports()
      .then(async () => {
        const s = await chrome.storage.local.get(["reportRetryQueue"]);
        const queue = Array.isArray(s.reportRetryQueue) ? s.reportRetryQueue : [];
        sendResponse({ ok: true, queueSize: queue.length });
      })
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (message?.type === "CONTENT_SCRIPT_READY") {
    sendResponse({ ok: true, url: sender?.url || "" });
    return;
  }

  if (message?.type === "GET_COLLECT_CONFIG") {
    chrome.storage.local
      .get(["autoCollectEnabled", "minCollectIntervalMs", "lastCollectAtMs"])
      .then((state) =>
        sendResponse({
          ok: true,
          autoCollectEnabled: state.autoCollectEnabled !== false,
          minCollectIntervalMs: Number(state.minCollectIntervalMs || 120000),
          lastCollectAtMs: Number(state.lastCollectAtMs || 0),
        })
      );
    return true;
  }

  if (message?.type === "SET_COLLECT_CONFIG") {
    const enabled = message.enabled !== false;
    let interval = Number(message.intervalMs || 120000);
    if (Number.isNaN(interval) || interval < 10000) interval = 10000;
    chrome.storage.local
      .set({ autoCollectEnabled: enabled, minCollectIntervalMs: interval })
      .then(() => sendResponse({ ok: true, autoCollectEnabled: enabled, minCollectIntervalMs: interval }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (message?.type === "GET_LAST_REPORT") {
    chrome.storage.local.get(["lastAutoReport"]).then((state) => {
      sendResponse({ ok: true, lastAutoReport: state.lastAutoReport || null });
    });
    return true;
  }

  if (message?.type === "GET_REPORT_HISTORY") {
    chrome.storage.local.get(["autoReportHistory"]).then((state) => {
      sendResponse({ ok: true, history: Array.isArray(state.autoReportHistory) ? state.autoReportHistory : [] });
    });
    return true;
  }

  if (message?.type === "GET_ALIAS_MAP") {
    chrome.storage.local.get(["competitorAliasMap"]).then((state) => {
      sendResponse({ ok: true, aliasMap: state.competitorAliasMap || {} });
    });
    return true;
  }

  if (message?.type === "GET_LAST_UNMATCHED") {
    chrome.storage.local.get(["lastUnmatchedCompetitors"]).then((state) => {
      sendResponse({
        ok: true,
        unmatched: Array.isArray(state.lastUnmatchedCompetitors) ? state.lastUnmatchedCompetitors : [],
      });
    });
    return true;
  }

  if (message?.type === "SET_ALIAS_MAP") {
    const aliasMap = message.aliasMap && typeof message.aliasMap === "object" ? message.aliasMap : {};
    chrome.storage.local
      .set({ competitorAliasMap: aliasMap })
      .then(() => sendResponse({ ok: true, aliasMap }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (message?.type === "APPEND_ALIAS_HISTORY") {
    const changes = Array.isArray(message.changes) ? message.changes : [];
    if (!changes.length) {
      sendResponse({ ok: true, appended: 0 });
      return;
    }
    chrome.storage.local.get(["aliasChangeHistory"]).then((state) => {
      const history = Array.isArray(state.aliasChangeHistory) ? state.aliasChangeHistory : [];
      const now = new Date().toISOString();
      for (const c of changes) {
        history.unshift({
          time: now,
          alias: c.alias || "",
          from: c.from || "",
          to: c.to || "",
        });
      }
      chrome.storage.local
        .set({ aliasChangeHistory: history.slice(0, 10) })
        .then(() => sendResponse({ ok: true, appended: changes.length }))
        .catch((err) => sendResponse({ ok: false, error: String(err) }));
    });
    return true;
  }

  if (message?.type === "GET_ALIAS_HISTORY") {
    chrome.storage.local.get(["aliasChangeHistory"]).then((state) => {
      sendResponse({
        ok: true,
        history: Array.isArray(state.aliasChangeHistory) ? state.aliasChangeHistory : [],
      });
    });
    return true;
  }

  if (message?.type === "CLEAR_ALIAS_HISTORY") {
    chrome.storage.local
      .set({ aliasChangeHistory: [] })
      .then(() => sendResponse({ ok: true }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (message?.type === "SET_ALIAS_HISTORY") {
    const history = Array.isArray(message.history) ? message.history : [];
    const normalized = history.slice(0, 10).map((item) => ({
      time: String(item?.time || new Date().toISOString()),
      alias: String(item?.alias || ""),
      from: String(item?.from || ""),
      to: String(item?.to || ""),
    }));
    chrome.storage.local
      .set({ aliasChangeHistory: normalized })
      .then(() => sendResponse({ ok: true, count: normalized.length }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
});
