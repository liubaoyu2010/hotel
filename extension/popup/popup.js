function byId(id) {
  return document.getElementById(id);
}

let cachedCompetitorNames = [];
let currentSuggestions = [];
let suggestThreshold = 0.45;

function setStatus(text, isError = false) {
  const el = byId("status");
  el.textContent = text;
  el.className = isError ? "err" : "ok";
}

function setOutput(data) {
  byId("output").textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function parseAliasMapText() {
  try {
    return JSON.parse(byId("aliasMapText").value || "{}");
  } catch (_e) {
    return null;
  }
}

async function requestApi(path, options = {}) {
  const state = await chrome.storage.local.get(["apiBase", "jwtToken"]);
  const apiBase = state.apiBase || byId("apiBase").value.trim();
  const headers = options.headers || {};
  if (state.jwtToken) headers.Authorization = `Bearer ${state.jwtToken}`;
  const res = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  });
  const data = await res.json();
  return { res, data };
}

async function loadState() {
  const state = await chrome.storage.local.get([
    "apiBase",
    "username",
    "jwtToken",
    "extensionToken",
    "deviceId",
    "autoCollectEnabled",
    "minCollectIntervalMs",
  ]);
  if (state.apiBase) byId("apiBase").value = state.apiBase;
  if (state.username) byId("username").value = state.username;
  if (state.deviceId) byId("deviceId").value = state.deviceId;
  byId("autoCollectEnabled").checked = state.autoCollectEnabled !== false;
  byId("minCollectIntervalSec").value = String(
    Math.max(10, Math.floor(Number(state.minCollectIntervalMs || 120000) / 1000))
  );
  suggestThreshold = Number(state.suggestThreshold ?? 0.45);
  if (Number.isNaN(suggestThreshold) || suggestThreshold < 0 || suggestThreshold > 1) {
    suggestThreshold = 0.45;
  }
  byId("suggestThreshold").value = String(suggestThreshold);
  await loadAliasMap();
  await loadCompetitorsForMapping();
  refreshAliasHistory();
  refreshUnmatched();
  refreshLastReport();
  refreshReportHistory();
}

async function saveBaseAndUser() {
  await chrome.storage.local.set({
    apiBase: byId("apiBase").value.trim(),
    username: byId("username").value.trim(),
  });
}

async function login() {
  await saveBaseAndUser();
  const apiBase = byId("apiBase").value.trim();
  const username = byId("username").value.trim();
  const password = byId("password").value;

  const res = await fetch(`${apiBase}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  setOutput(data);
  if (res.ok && data?.data?.access_token) {
    await chrome.storage.local.set({ jwtToken: data.data.access_token, username });
    setStatus("Login success");
  } else {
    setStatus("Login failed", true);
  }
}

async function bindExtension() {
  const apiBase = byId("apiBase").value.trim();
  const deviceId = byId("deviceId").value.trim() || crypto.randomUUID();
  byId("deviceId").value = deviceId;
  const state = await chrome.storage.local.get(["jwtToken"]);
  if (!state.jwtToken) {
    setStatus("Please login first", true);
    return;
  }

  const res = await fetch(`${apiBase}/api/v1/extension/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${state.jwtToken}`,
    },
    body: JSON.stringify({ device_id: deviceId, version: "0.1.0" }),
  });
  const data = await res.json();
  setOutput(data);
  if (res.ok && data?.data?.extension_token) {
    await chrome.storage.local.set({
      extensionToken: data.data.extension_token,
      deviceId,
    });
    setStatus("Bind success");
  } else {
    setStatus("Bind failed", true);
  }
}

async function reportTestData() {
  const apiBase = byId("apiBase").value.trim();
  const competitorName = byId("competitorName").value.trim();
  const roomType = byId("roomType").value.trim();
  const price = Number(byId("price").value);
  const state = await chrome.storage.local.get(["extensionToken"]);
  if (!state.extensionToken) {
    setStatus("Please bind extension first", true);
    return;
  }

  const body = {
    type: "competitor",
    source: "meituan_merchant",
    data: {
      competitors: [
        {
          name: competitorName,
          room_type: roomType,
          price,
          availability: true,
        },
      ],
      business: {},
      benchmark: {},
    },
    url: "https://e.meituan.com/mock",
    captured_at: new Date().toISOString(),
  };

  const res = await fetch(`${apiBase}/api/v1/extension/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Extension-Token": state.extensionToken,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  setOutput(data);
  if (res.ok) {
    await chrome.storage.local.set({
      lastUnmatchedCompetitors: data?.data?.unmatched_competitors || [],
    });
    refreshUnmatched();
    setStatus("Report success");
  } else setStatus("Report failed", true);
}

async function queueStatus() {
  chrome.runtime.sendMessage({ type: "QUEUE_STATUS" }, (resp) => {
    if (!resp?.ok) {
      setStatus("Queue status failed", true);
      setOutput(resp || { error: "unknown" });
      return;
    }
    setStatus(`Queue size: ${resp.queueSize}`);
    setOutput(resp);
  });
}

async function retryQueue() {
  chrome.runtime.sendMessage({ type: "FORCE_RETRY_QUEUE" }, (resp) => {
    if (!resp?.ok) {
      setStatus("Retry queue failed", true);
      setOutput(resp || { error: "unknown" });
      return;
    }
    setStatus(`Retry done, queue size: ${resp.queueSize}`);
    setOutput(resp);
  });
}

function refreshLastReport() {
  chrome.runtime.sendMessage({ type: "GET_LAST_REPORT" }, (resp) => {
    if (!resp?.ok) {
      byId("lastReport").textContent = JSON.stringify(resp || { error: "unknown" }, null, 2);
      return;
    }
    byId("lastReport").textContent = JSON.stringify(resp.lastAutoReport, null, 2);
  });
}

function refreshReportHistory() {
  chrome.runtime.sendMessage({ type: "GET_REPORT_HISTORY" }, (resp) => {
    if (!resp?.ok) {
      byId("reportHistory").textContent = JSON.stringify(resp || { error: "unknown" }, null, 2);
      return;
    }
    byId("reportHistory").textContent = JSON.stringify(resp.history || [], null, 2);
  });
}

async function loadAliasMap() {
  const { res, data } = await requestApi("/api/v1/competitor-aliases", {
    method: "GET",
    headers: {},
  });
  if (!res.ok) {
    byId("aliasMapText").value = "{}";
    return;
  }
  byId("aliasMapText").value = JSON.stringify(data?.data?.alias_map || {}, null, 2);
  byId("aliasMapText").dataset.prev = JSON.stringify(data?.data?.alias_map || {});
  // keep local mirror for content-script fast mapping
  const localNormalized = {};
  for (const [k, v] of Object.entries(data?.data?.alias_map || {})) {
    localNormalized[String(k).trim().toLowerCase()] = String(v).trim();
  }
  chrome.runtime.sendMessage({ type: "SET_ALIAS_MAP", aliasMap: localNormalized }, () => {
    void chrome.runtime.lastError;
  });
}

async function saveAliasMap() {
  const parsed = parseAliasMapText();
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    setStatus("Alias map JSON invalid", true);
    return;
  }
  const normalized = {};
  const changes = [];
  const oldMap = JSON.parse(byId("aliasMapText").dataset.prev || "{}");
  for (const [k, v] of Object.entries(parsed)) {
    if (!k || !v) continue;
    const kk = String(k).trim().toLowerCase();
    const vv = String(v).trim();
    normalized[kk] = vv;
    if (oldMap[kk] !== vv) {
      changes.push({ alias: kk, from: oldMap[kk] || "", to: vv });
    }
  }
  const { res, data } = await requestApi("/api/v1/competitor-aliases", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alias_map: normalized }),
  });
  if (!res.ok) {
    setStatus("Save alias map failed", true);
    setOutput(data || { error: "unknown" });
    return;
  }
  chrome.runtime.sendMessage({ type: "SET_ALIAS_MAP", aliasMap: normalized }, () => {
    void chrome.runtime.lastError;
  });
  chrome.runtime.sendMessage({ type: "APPEND_ALIAS_HISTORY", changes }, () => {
    void chrome.runtime.lastError;
  });
  byId("aliasMapText").dataset.prev = JSON.stringify(normalized);
  setStatus("Alias map saved");
  setOutput(data);
  refreshAliasHistory();
}

async function loadCompetitorsForMapping() {
  const { res, data } = await requestApi("/api/v1/competitors", { method: "GET", headers: {} });
  const select = byId("canonicalCompetitor");
  select.innerHTML = "";
  cachedCompetitorNames = [];
  if (!res.ok) return;
  const items = data?.data?.items || [];
  for (const it of items) {
    cachedCompetitorNames.push(it.name);
    const op = document.createElement("option");
    op.value = it.name;
    op.textContent = it.name;
    select.appendChild(op);
  }
}

function refreshUnmatched() {
  chrome.runtime.sendMessage({ type: "GET_LAST_UNMATCHED" }, (resp) => {
    if (!resp?.ok) return;
    byId("unmatchedList").textContent = JSON.stringify(resp.unmatched || [], null, 2);
  });
}

function refreshAliasHistory() {
  chrome.runtime.sendMessage({ type: "GET_ALIAS_HISTORY" }, (resp) => {
    const container = byId("aliasHistory");
    if (!resp?.ok) {
      container.textContent = JSON.stringify(resp || { error: "unknown" }, null, 2);
      return;
    }
    const history = Array.isArray(resp.history) ? resp.history : [];
    container.innerHTML = "";
    if (!history.length) {
      container.textContent = "[]";
      return;
    }
    history.forEach((item, idx) => {
      const row = document.createElement("div");
      row.className = "history-item";
      const meta = document.createElement("div");
      meta.className = "history-meta";
      meta.textContent = `${item.time || ""}`;
      const text = document.createElement("div");
      text.textContent = `${item.alias || ""}: ${item.from || "(empty)"} -> ${item.to || "(empty)"}`;
      const rollbackBtn = document.createElement("button");
      rollbackBtn.className = "history-rollback";
      rollbackBtn.textContent = "Rollback";
      rollbackBtn.addEventListener("click", () => rollbackAliasChange(item, idx + 1));
      row.appendChild(meta);
      row.appendChild(text);
      row.appendChild(rollbackBtn);
      container.appendChild(row);
    });
  });
}

async function getAliasHistory() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "GET_ALIAS_HISTORY" }, (resp) => {
      if (!resp?.ok) {
        resolve([]);
        return;
      }
      resolve(Array.isArray(resp.history) ? resp.history : []);
    });
  });
}

function parseAliasSnapshotText() {
  try {
    return JSON.parse(byId("aliasSnapshotText").value || "{}");
  } catch (_e) {
    return null;
  }
}

function calcMapDiffStats(currentMap, incomingMap, strategy) {
  const current = currentMap && typeof currentMap === "object" ? currentMap : {};
  const incoming = incomingMap && typeof incomingMap === "object" ? incomingMap : {};
  let added = 0;
  let updated = 0;
  let removed = 0;
  for (const [k, v] of Object.entries(incoming)) {
    if (!(k in current)) {
      added += 1;
      continue;
    }
    if (String(current[k]) !== String(v)) updated += 1;
  }
  if (strategy === "replace") {
    for (const k of Object.keys(current)) {
      if (!(k in incoming)) removed += 1;
    }
  }
  return { added, updated, removed };
}

async function validateAliasMapAfterImport(aliasMap, sampleSize = 5) {
  const { res, data } = await requestApi("/api/v1/competitors", { method: "GET", headers: {} });
  if (!res.ok) {
    return {
      ok: false,
      reason: "load_competitors_failed",
      detail: data || {},
    };
  }
  const competitorNames = (data?.data?.items || []).map((it) => String(it.name || "").trim());
  const competitorSet = new Set(competitorNames);
  const entries = Object.entries(aliasMap || {});
  const invalid = [];
  for (const [alias, canonical] of entries) {
    if (!competitorSet.has(String(canonical))) {
      invalid.push({ alias, canonical });
    }
  }
  const sample = entries.slice(0, Math.max(1, sampleSize)).map(([alias, canonical]) => ({
    alias,
    canonical,
    canonical_exists: competitorSet.has(String(canonical)),
  }));
  return {
    ok: true,
    total_aliases: entries.length,
    total_competitors: competitorNames.length,
    invalid_count: invalid.length,
    invalid_examples: invalid.slice(0, 10),
    sample,
  };
}

async function exportAliasSnapshot() {
  const aliasMap = parseAliasMapText();
  if (!aliasMap || typeof aliasMap !== "object" || Array.isArray(aliasMap)) {
    setStatus("Alias map JSON invalid", true);
    return;
  }
  const history = await getAliasHistory();
  const snapshot = {
    version: 1,
    exportedAt: new Date().toISOString(),
    suggestThreshold,
    aliasMap,
    aliasHistory: history,
  };
  const text = JSON.stringify(snapshot, null, 2);
  byId("aliasSnapshotText").value = text;
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Snapshot exported and copied");
      return;
    } catch (_e) {
      // ignore clipboard failure, snapshot already in textarea
    }
  }
  setStatus("Snapshot exported");
}

async function importAliasSnapshot() {
  const snapshot = parseAliasSnapshotText();
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
    setStatus("Snapshot JSON invalid", true);
    return;
  }
  const importMode = byId("aliasSnapshotImportMode").value || "all";
  const importMap = importMode === "all" || importMode === "map";
  const importHistory = importMode === "all" || importMode === "history";
  const importThreshold = importMode === "all";
  const mapStrategy = byId("aliasSnapshotMapStrategy").value || "replace";
  const aliasMapRaw = snapshot.aliasMap;
  const aliasHistoryRaw = snapshot.aliasHistory;
  const thresholdRaw = snapshot.suggestThreshold;
  if (importMap && (!aliasMapRaw || typeof aliasMapRaw !== "object" || Array.isArray(aliasMapRaw))) {
    setStatus("Snapshot aliasMap invalid", true);
    return;
  }
  if (importHistory && !Array.isArray(aliasHistoryRaw)) {
    setStatus("Snapshot aliasHistory invalid", true);
    return;
  }
  const mapCount = importMap ? Object.keys(aliasMapRaw || {}).length : 0;
  const historyCount = importHistory ? (Array.isArray(aliasHistoryRaw) ? aliasHistoryRaw.length : 0) : 0;
  let mapStats = { added: 0, updated: 0, removed: 0 };
  if (importMap) {
    const imported = {};
    for (const [k, v] of Object.entries(aliasMapRaw || {})) {
      if (!k || !v) continue;
      imported[String(k).trim().toLowerCase()] = String(v).trim();
    }
    const current = parseAliasMapText();
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      setStatus("Alias map JSON invalid", true);
      return;
    }
    mapStats = calcMapDiffStats(current, imported, mapStrategy);
  }
  const confirmed = window.confirm(
    `Import snapshot?\n\nmode: ${importMode}\nmap strategy: ${
      importMap ? mapStrategy : "n/a"
    }\naliasMap keys: ${mapCount}\naliasHistory rows: ${historyCount}${
      importMap
        ? `\nmap preview: +${mapStats.added} / ~${mapStats.updated} / -${mapStats.removed}`
        : ""
    }`
  );
  if (!confirmed) {
    setStatus("Import snapshot cancelled");
    return;
  }

  if (importMap) {
    const imported = {};
    for (const [k, v] of Object.entries(aliasMapRaw)) {
      if (!k || !v) continue;
      imported[String(k).trim().toLowerCase()] = String(v).trim();
    }
    let nextMap = imported;
    if (mapStrategy === "merge") {
      const current = parseAliasMapText();
      if (!current || typeof current !== "object" || Array.isArray(current)) {
        setStatus("Alias map JSON invalid", true);
        return;
      }
      nextMap = { ...current, ...imported };
    }
    byId("aliasMapText").value = JSON.stringify(nextMap, null, 2);
    byId("aliasMapText").dataset.prev = JSON.stringify(nextMap);
    await saveAliasMap();
    const validation = await validateAliasMapAfterImport(nextMap, 5);
    setOutput({ import_result: { mode: importMode, map_strategy: mapStrategy }, validation });
    if (!validation.ok) {
      setStatus("Snapshot imported, validation failed to run", true);
      return;
    }
    if (validation.invalid_count > 0) {
      setStatus(
        `Snapshot imported (${importMode}), validation warning: ${validation.invalid_count} invalid canonical`,
        true
      );
    } else {
      setStatus(`Snapshot imported (${importMode}), validation passed`);
    }
  }

  if (importHistory) {
    await new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: "SET_ALIAS_HISTORY", history: aliasHistoryRaw }, () => resolve());
    });
  }

  if (importThreshold && typeof thresholdRaw === "number" && thresholdRaw >= 0 && thresholdRaw <= 1) {
    suggestThreshold = thresholdRaw;
    byId("suggestThreshold").value = String(suggestThreshold);
    await chrome.storage.local.set({ suggestThreshold });
  }

  refreshAliasHistory();
  if (!importMap) setStatus(`Snapshot imported (${importMode})`);
}

async function rollbackAliasChange(item, index) {
  const alias = String(item?.alias || "").trim().toLowerCase();
  if (!alias) {
    setStatus("Rollback failed: invalid alias", true);
    return;
  }
  const confirmed = window.confirm(
    `Rollback #${index}?\n\n${alias}: ${item?.to || "(empty)"} -> ${item?.from || "(empty)"}`
  );
  if (!confirmed) {
    setStatus("Rollback cancelled");
    return;
  }
  const current = parseAliasMapText();
  if (!current || typeof current !== "object" || Array.isArray(current)) {
    setStatus("Alias map JSON invalid", true);
    return;
  }
  if (item?.from) current[alias] = String(item.from);
  else delete current[alias];
  byId("aliasMapText").value = JSON.stringify(current, null, 2);
  await saveAliasMap();
  setStatus(`Rollback applied for: ${alias}`);
}

async function undoLatestAliasChange() {
  const history = await getAliasHistory();
  if (!history.length) {
    setStatus("No alias history to undo", true);
    return;
  }
  await rollbackAliasChange(history[0], 1);
}

async function clearAliasHistory() {
  const confirmed = window.confirm("Clear all alias change history?");
  if (!confirmed) {
    setStatus("Clear history cancelled");
    return;
  }
  chrome.runtime.sendMessage({ type: "CLEAR_ALIAS_HISTORY" }, (resp) => {
    if (!resp?.ok) {
      setStatus("Clear alias history failed", true);
      setOutput(resp || { error: "unknown" });
      return;
    }
    refreshAliasHistory();
    setStatus("Alias history cleared");
  });
}

function normalizeName(s) {
  return String(s || "").trim().toLowerCase();
}

function scoreNameSimilarity(raw, canonical) {
  const a = normalizeName(raw);
  const b = normalizeName(canonical);
  if (!a || !b) return 0;
  if (a === b) return 1;
  if (a.includes(b) || b.includes(a)) return 0.9;
  const aSet = new Set(a.split(""));
  const bSet = new Set(b.split(""));
  let common = 0;
  for (const ch of aSet) if (bSet.has(ch)) common += 1;
  return common / Math.max(aSet.size, bSet.size, 1);
}

function buildSuggestedMap(unmatched, canonicalNames) {
  const suggestionItems = [];
  for (const raw of unmatched) {
    let best = "";
    let bestScore = 0;
    for (const c of canonicalNames) {
      const score = scoreNameSimilarity(raw, c);
      if (score > bestScore) {
        bestScore = score;
        best = c;
      }
    }
    if (best && bestScore >= 0.35) {
      suggestionItems.push({
        raw: raw,
        aliasKey: normalizeName(raw),
        canonical: best,
        score: bestScore,
        selected: bestScore >= suggestThreshold,
      });
    }
  }
  return suggestionItems;
}

function renderSuggestions() {
  const container = byId("suggestionsList");
  container.innerHTML = "";
  if (!currentSuggestions.length) {
    container.textContent = "No suggestions";
    return;
  }
  currentSuggestions.forEach((s, idx) => {
    const row = document.createElement("label");
    row.className = "suggestion-item";
    if (s.score < suggestThreshold) row.classList.add("low-score");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = s.selected;
    checkbox.addEventListener("change", () => {
      currentSuggestions[idx].selected = checkbox.checked;
    });

    const score = document.createElement("span");
    score.className = "score";
    score.textContent = `score:${s.score.toFixed(2)}`;

    const text = document.createElement("span");
    text.textContent = `${s.raw} -> ${s.canonical}`;

    row.appendChild(checkbox);
    row.appendChild(score);
    row.appendChild(text);
    container.appendChild(row);
  });
}

async function suggestMapping() {
  const unmatchedResp = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "GET_LAST_UNMATCHED" }, (resp) => resolve(resp || {}));
  });
  const unmatched = Array.isArray(unmatchedResp.unmatched) ? unmatchedResp.unmatched : [];
  currentSuggestions = buildSuggestedMap(unmatched, cachedCompetitorNames);
  renderSuggestions();
  if (currentSuggestions.length) setStatus("Suggested mapping generated");
  else setStatus("No strong suggestion found", true);
}

async function applySuggestedMapping() {
  const selected = currentSuggestions.filter((x) => x.selected);
  if (!selected.length) {
    setStatus("No selected suggestion", true);
    return;
  }
  const previewLines = selected.map(
    (s) => `- ${s.raw} -> ${s.canonical} (score=${s.score.toFixed(2)})`
  );
  const confirmed = window.confirm(
    `Apply ${selected.length} selected mappings?\n\n${previewLines.join("\n")}`
  );
  if (!confirmed) {
    setStatus("Apply cancelled");
    return;
  }
  const current = parseAliasMapText();
  if (!current || typeof current !== "object" || Array.isArray(current)) {
    setStatus("Alias map JSON invalid", true);
    return;
  }
  for (const item of selected) {
    current[item.aliasKey] = item.canonical;
  }
  const merged = { ...current };
  byId("aliasMapText").value = JSON.stringify(merged, null, 2);
  await saveAliasMap();
}

async function mapUnmatchedToSelected() {
  const canonical = byId("canonicalCompetitor").value;
  if (!canonical) {
    setStatus("No canonical competitor selected", true);
    return;
  }
  const current = parseAliasMapText();
  if (!current || typeof current !== "object" || Array.isArray(current)) {
    setStatus("Alias map JSON invalid", true);
    return;
  }
  const unmatchedResp = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "GET_LAST_UNMATCHED" }, (resp) => resolve(resp || {}));
  });
  const unmatched = Array.isArray(unmatchedResp.unmatched) ? unmatchedResp.unmatched : [];
  for (const raw of unmatched) {
    current[String(raw).trim().toLowerCase()] = canonical;
  }
  byId("aliasMapText").value = JSON.stringify(current, null, 2);
  await saveAliasMap();
}

async function saveCollectConfig() {
  const enabled = byId("autoCollectEnabled").checked;
  let sec = Number(byId("minCollectIntervalSec").value || "120");
  if (Number.isNaN(sec) || sec < 10) sec = 10;
  chrome.runtime.sendMessage(
    {
      type: "SET_COLLECT_CONFIG",
      enabled,
      intervalMs: sec * 1000,
    },
    (resp) => {
      if (!resp?.ok) {
        setStatus("Save collect config failed", true);
        setOutput(resp || { error: "unknown" });
        return;
      }
      setStatus(
        `Collect config saved: enabled=${resp.autoCollectEnabled}, interval=${Math.floor(
          resp.minCollectIntervalMs / 1000
        )}s`
      );
      setOutput(resp);
    }
  );
}

async function saveSuggestThreshold() {
  let v = Number(byId("suggestThreshold").value || "0.45");
  if (Number.isNaN(v)) v = 0.45;
  if (v < 0) v = 0;
  if (v > 1) v = 1;
  suggestThreshold = v;
  await chrome.storage.local.set({ suggestThreshold: v });
  setStatus(`Suggest threshold saved: ${v.toFixed(2)}`);
}

byId("btnLogin").addEventListener("click", login);
byId("btnBind").addEventListener("click", bindExtension);
byId("btnReport").addEventListener("click", reportTestData);
byId("btnQueueStatus").addEventListener("click", queueStatus);
byId("btnRetryQueue").addEventListener("click", retryQueue);
byId("btnSaveCollectConfig").addEventListener("click", saveCollectConfig);
byId("btnSaveAliasMap").addEventListener("click", saveAliasMap);
byId("btnSuggestMapping").addEventListener("click", suggestMapping);
byId("btnSaveSuggestThreshold").addEventListener("click", saveSuggestThreshold);
byId("btnApplySuggested").addEventListener("click", applySuggestedMapping);
byId("btnMapUnmatched").addEventListener("click", mapUnmatchedToSelected);
byId("btnUndoLatestAlias").addEventListener("click", undoLatestAliasChange);
byId("btnClearAliasHistory").addEventListener("click", clearAliasHistory);
byId("btnExportAliasSnapshot").addEventListener("click", exportAliasSnapshot);
byId("btnImportAliasSnapshot").addEventListener("click", importAliasSnapshot);

loadState();
setInterval(refreshLastReport, 3000);
setInterval(refreshReportHistory, 5000);
setInterval(refreshUnmatched, 5000);
setInterval(refreshAliasHistory, 5000);
