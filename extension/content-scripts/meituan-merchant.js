(function initContentScript() {
  let collectTimer = null;

  function parsePrice(text) {
    if (!text) return null;
    const m = String(text).replace(/,/g, "").match(/(\d+(\.\d+)?)/);
    if (!m) return null;
    return Number(m[1]);
  }

  function textBySelectors(root, selectors) {
    for (const sel of selectors) {
      const el = root.querySelector(sel);
      if (el && el.textContent) return el.textContent.trim();
    }
    return "";
  }

  function collectCompetitors() {
    // Generic strategy for MVP:
    // 1) try known row-like selectors
    // 2) fallback to elements containing "¥/元"
    const rowSelectors = [
      ".competitor-item",
      ".table-row",
      ".ant-table-row",
      "tr",
      ".list-item",
    ];

    const rows = [];
    for (const sel of rowSelectors) {
      document.querySelectorAll(sel).forEach((el) => rows.push(el));
      if (rows.length >= 3) break;
    }

    const items = [];
    for (const row of rows) {
      const name = textBySelectors(row, [".hotel-name", ".name", "[data-name]", "td:nth-child(1)"]);
      const roomType = textBySelectors(row, [".room-type", ".type", "td:nth-child(2)"]) || "默认房型";
      const priceText =
        textBySelectors(row, [".price", ".amount", "td:nth-child(3)"]) || row.textContent || "";
      const price = parsePrice(priceText);
      if (!name || !price || Number.isNaN(price)) continue;
      items.push({
        name,
        room_type: roomType,
        price,
        availability: true,
      });
    }

    if (items.length) return items.slice(0, 20);

    // fallback: scan visible blocks with price-like text
    const fallback = [];
    document.querySelectorAll("div,li,tr").forEach((el) => {
      const t = (el.textContent || "").trim();
      if (!t || t.length < 6) return;
      if (!(/[¥￥]|元/.test(t))) return;
      const price = parsePrice(t);
      if (!price) return;
      const name = t.split(/\s+/)[0].slice(0, 30) || "未知竞品";
      fallback.push({
        name,
        room_type: "默认房型",
        price,
        availability: true,
      });
    });
    return fallback.slice(0, 10);
  }

  async function reportCollectedData() {
    chrome.runtime.sendMessage({ type: "GET_COLLECT_CONFIG" }, async (cfg) => {
      if (!cfg?.ok) return;
      if (!cfg.autoCollectEnabled) return;
      const now = Date.now();
      const minInterval = Number(cfg.minCollectIntervalMs || 120000);
      const last = Number(cfg.lastCollectAtMs || 0);
      if (now - last < minInterval) return;

      const competitors = collectCompetitors();
      if (!competitors.length) return;
      const payload = {
        type: "competitor",
        source: "meituan_merchant",
        data: { competitors, business: {}, benchmark: {} },
        url: window.location.href,
        captured_at: new Date().toISOString(),
      };
      chrome.runtime.sendMessage({ type: "REPORT_PAYLOAD", payload }, () => {
        void chrome.runtime.lastError;
      });
    });
  }

  function scheduleCollect() {
    if (collectTimer) clearTimeout(collectTimer);
    collectTimer = setTimeout(reportCollectedData, 2500);
  }

  const observer = new MutationObserver(() => {
    scheduleCollect();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  chrome.runtime.sendMessage({ type: "CONTENT_SCRIPT_READY" }, () => {
    void chrome.runtime.lastError;
  });
  scheduleCollect();
})();
