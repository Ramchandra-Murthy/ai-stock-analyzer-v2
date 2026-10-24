import { useEffect, useMemo, useState } from "react";

function Stat({ label, value, detail }) {
  return (
    <section className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </section>
  );
}

function isSafeJobId(value) {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}

function StockChart({ points }) {
  const validPoints = (points ?? []).filter((point) => Number.isFinite(point.Close));
  if (!validPoints.length) {
    return <p className="empty">No chart history available for this stock.</p>;
  }

  const width = 760;
  const height = 260;
  const padding = 28;
  const values = validPoints.flatMap((point) =>
    ["Close", "SMA_20", "SMA_50"]
      .map((key) => point[key])
      .filter(Number.isFinite),
  );
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const x = (index) =>
    padding + (index * (width - padding * 2)) / Math.max(validPoints.length - 1, 1);
  const y = (value) =>
    height - padding - ((value - min) * (height - padding * 2)) / range;
  const pathFor = (key) =>
    validPoints
      .filter((point) => Number.isFinite(point[key]))
      .map((point, index, series) => {
        const originalIndex = validPoints.indexOf(point);
        return `${index === 0 ? "M" : "L"} ${x(originalIndex).toFixed(1)} ${y(point[key]).toFixed(1)}`;
      })
      .join(" ");

  return (
    <div className="stock-chart">
      <div className="chart-legend">
        <span>● Close</span><span>● SMA 20</span><span>● SMA 50</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Stock price and moving average chart">
        <path className="chart-grid" d={`M ${padding} ${padding} H ${width - padding} M ${padding} ${height / 2} H ${width - padding} M ${padding} ${height - padding} H ${width - padding}`} />
        <path className="chart-line chart-close" d={pathFor("Close")} />
        <path className="chart-line chart-sma20" d={pathFor("SMA_20")} />
        <path className="chart-line chart-sma50" d={pathFor("SMA_50")} />
      </svg>
      <div className="chart-axis"><span>Older</span><span>Latest</span></div>
    </div>
  );
}


function readDashboardPreference(key, fallback) {
  try {
    const value = window.localStorage.getItem(`eros-dashboard-${key}`);
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

function writeDashboardPreference(key, value) {
  try {
    window.localStorage.setItem(`eros-dashboard-${key}`, value);
  } catch {
    // Ignore unavailable browser storage.
  }
}

function clearDashboardPreferences() {
  try {
    [
      "view",
      "exchange",
      "lookback",
      "jump",
      "table-exchange",
      "sort-key",
      "sort-direction",
      "table-density",
      "auto-refresh-interval",
    ].forEach((key) => window.localStorage.removeItem(`eros-dashboard-${key}`));
  } catch {
    // Ignore unavailable browser storage.
  }
}

function SortHeader({ label, column, sortKey, sortDirection, onSort }) {
  const active = sortKey === column;
  const direction = active ? (sortDirection === "asc" ? "ascending" : "descending") : "none";
  const indicator = active ? (sortDirection === "asc" ? " ↑" : " ↓") : "";

  return (
    <th aria-sort={direction}>
      <button
        className="table-sort"
        onClick={() => onSort(column)}
        aria-label={`Sort by ${label}${active ? `, currently ${direction}` : ""}`}
      >
        {label}{indicator}
      </button>
    </th>
  );
}

function App() {
  const [health, setHealth] = useState("checking");
  const [rows, setRows] = useState([]);
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState("Ready");
  const [jobId, setJobId] = useState(null);
  const [exchange, setExchange] = useState(() => readDashboardPreference("exchange", "Both"));
  const [lookback, setLookback] = useState(() => readDashboardPreference("lookback", "5"));
  const [jump, setJump] = useState(() => readDashboardPreference("jump", "1"));
  const [view, setView] = useState(() => readDashboardPreference("view", "price-pulse"));
  const [marketRows, setMarketRows] = useState([]);
  const [unusualRows, setUnusualRows] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(() => readDashboardPreference("auto-refresh-interval", "60"));
  const [nextAutoScanAt, setNextAutoScanAt] = useState(null);
  const [autoRefreshCountdown, setAutoRefreshCountdown] = useState(null);
  const [refreshStartedAt, setRefreshStartedAt] = useState(null);
  const [refreshDurationMs, setRefreshDurationMs] = useState(null);
  const [refreshError, setRefreshError] = useState(null);
  const [refreshAgeSeconds, setRefreshAgeSeconds] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tableExchange, setTableExchange] = useState(() => readDashboardPreference("table-exchange", "All"));
  const [sortKey, setSortKey] = useState(() => readDashboardPreference("sort-key", "Symbol"));
  const [sortDirection, setSortDirection] = useState(() => readDashboardPreference("sort-direction", "asc"));
  const [tableDensity, setTableDensity] = useState(() => readDashboardPreference("table-density", "comfortable"));
  const [tableSearch, setTableSearch] = useState("");
  const [signalRefreshing, setSignalRefreshing] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockDetail, setStockDetail] = useState(null);
  const [stockDetailLoading, setStockDetailLoading] = useState(false);
  const [stockDetailError, setStockDetailError] = useState(null);
  const [stockDetailUpdatedAt, setStockDetailUpdatedAt] = useState(null);
  const [expandedHistoryJob, setExpandedHistoryJob] = useState(null);
  const [optionsUnderlying, setOptionsUnderlying] = useState("NIFTY");
  const [optionsExpiry, setOptionsExpiry] = useState("");
  const [optionsData, setOptionsData] = useState(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState(null);
  const [optionsUpdatedAt, setOptionsUpdatedAt] = useState(null);

  useEffect(() => {
    writeDashboardPreference("view", view);
    writeDashboardPreference("exchange", exchange);
    writeDashboardPreference("lookback", lookback);
    writeDashboardPreference("jump", jump);
    writeDashboardPreference("table-exchange", tableExchange);
    writeDashboardPreference("sort-key", sortKey);
    writeDashboardPreference("sort-direction", sortDirection);
    writeDashboardPreference("table-density", tableDensity);
    writeDashboardPreference("auto-refresh-interval", autoRefreshInterval);
  }, [autoRefreshInterval, exchange, jump, lookback, sortDirection, sortKey, tableDensity, tableExchange, view]);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.ok ? r.json() : Promise.reject(new Error("API unavailable")))
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
    void refreshHistory();
    void refreshHealth();
    const healthTimer = setInterval(() => {
      void refreshHealth();
      void refreshHistory();
    }, 15000);
    return () => clearInterval(healthTimer);
  }, []);

  useEffect(() => {
    function handleDashboardShortcut(event) {
      const target = event.target;
      const tagName = target?.tagName;
      if (
        target?.isContentEditable ||
        ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(tagName)
      ) {
        return;
      }

      if (event.key === "1") {
        setView("price-pulse");
      } else if (event.key === "2") {
        setView("unusual");
      } else if (event.key === "3") {
        setView("market");
      } else if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        document.getElementById("stock-search")?.focus();
      } else if (event.key.toLowerCase() === "e") {
        event.preventDefault();
        exportVisibleRows();
      } else if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        void refreshSignalBoard();
      } else if (event.key === "Escape" && tableSearch) {
        setTableSearch("");
      }
    }

    window.addEventListener("keydown", handleDashboardShortcut);
    return () => window.removeEventListener("keydown", handleDashboardShortcut);
  }, [tableSearch]);

  useEffect(() => {
    if (!jobId || !isSafeJobId(jobId)) {
      if (jobId) setStatus("Invalid job id");
      return undefined;
    }
    const safeJobId = encodeURIComponent(jobId);
    const timer = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/v1/intraday/price-jumps/jobs/${safeJobId}`,
        );
        const job = await response.json();
        setStatus(job.status ?? "unknown");
        if (job.status === "completed") {
          setRows(job.results ?? []);
          setJobId(null);
          setLastUpdated(new Date().toISOString());
          void refreshHistory();
          void refreshHealth();
          clearInterval(timer);
        }
        if (job.status === "failed") {
          setJobId(null);
          clearInterval(timer);
        }
      } catch {
        setStatus("API error");
        setJobId(null);
        clearInterval(timer);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId]);

  async function refreshHealth() {
    try {
      const response = await fetch("/api/v1/intraday/health");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Health unavailable");
      setSystemHealth(data);
    } catch {
      setSystemHealth(null);
    }
  }

  async function loadOptionsChain(expiryOverride = optionsExpiry) {
    setOptionsLoading(true);
    setOptionsError(null);
    setStatus("Loading options analytics");
    try {
      const params = new URLSearchParams({ underlying: optionsUnderlying });
      if (expiryOverride) params.set("expiry", expiryOverride);
      const response = await fetch(`/api/v1/options/chain?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to load options analytics");
      setOptionsData(data);
      setOptionsExpiry(data.expiry ?? "");
      setOptionsUpdatedAt(new Date().toISOString());
      setStatus("Ready");
    } catch (error) {
      setOptionsData(null);
      setOptionsError(error.message);
      setStatus(error.message);
    } finally {
      setOptionsLoading(false);
    }
  }

  async function loadUnusualActivity() {
    setStatus("Loading unusual activity");
    try {
      const params = new URLSearchParams({
        limit: "20",
        exchange_category: exchange,
      });
      const response = await fetch(
        `/api/v1/intraday/unusual-activity?${params.toString()}`,
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to load activity");
      setUnusualRows(data.results ?? []);
      setView("unusual");
      setStatus("Ready");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadMarketScanner() {
    setStatus("Loading market scanner");
    try {
      const response = await fetch("/api/v1/scanner/market?limit=20");
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to load market scan");
      setMarketRows(data.results ?? []);
      setView("market");
      setStatus("Ready");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function refreshHistory() {
    try {
      const response = await fetch("/api/v1/intraday/history?limit=10");
      const data = await response.json();
      setHistory(data.scans ?? []);
    } catch {
      setHistory([]);
    }
  }

  async function loadStockDetail(symbol, rowExchange = "NSE") {
    if (typeof symbol !== "string" || !/^[A-Za-z0-9&-]{1,20}$/.test(symbol)) {
      setStatus("Invalid stock symbol");
      return;
    }
    const safeSymbol = encodeURIComponent(symbol.toUpperCase());
    const safeExchange = rowExchange === "BSE" ? "BSE" : "NSE";
    setSelectedStock({ symbol: symbol.toUpperCase(), exchange: safeExchange });
    setStockDetailLoading(true);
    setStockDetailError(null);
    setStatus("Loading stock detail");
    try {
      const response = await fetch(
        `/api/v1/scanner/stock?symbol=${safeSymbol}&exchange=${safeExchange}`,
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to load stock detail");
      setStockDetail(data);
      setStockDetailUpdatedAt(new Date().toISOString());
      setStatus("Ready");
    } catch (error) {
      setStockDetail(null);
      setStockDetailError(error.message);
      setStatus(error.message);
    } finally {
      setStockDetailLoading(false);
    }
  }

  function exportVisibleRows() {
    if (!visibleRows.length) {
      setStatus("No visible rows to export");
      return;
    }
    const columns = Array.from(
      new Set(visibleRows.flatMap((row) => Object.keys(row))),
    );
    const escapeCsv = (value) => {
      const text = value == null ? "" : String(value);
      return /[",\\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    const csv = [
      columns.map(escapeCsv).join(","),
      ...visibleRows.map((row) => columns.map((column) => escapeCsv(row[column])).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const viewName = view.replace(/[^a-z0-9-]+/gi, "-");
    link.href = url;
    link.download = `eros-${viewName}-signals.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus(`Exported ${visibleRows.length} rows`);
  }

  async function refreshSignalBoard() {
    const refreshStarted = Date.now();
    setSignalRefreshing(true);
    setRefreshError(null);
    setStatus("Refreshing signals");
    try {
      const activityParams = new URLSearchParams({
        limit: "20",
        exchange_category: exchange,
      });
      const [activityResponse, marketResponse] = await Promise.all([
        fetch(`/api/v1/intraday/unusual-activity?${activityParams.toString()}`),
        fetch("/api/v1/scanner/market?limit=20"),
      ]);
      const activityData = await activityResponse.json();
      const marketData = await marketResponse.json();
      if (!activityResponse.ok) {
        throw new Error(activityData.detail ?? "Unable to load activity");
      }
      if (!marketResponse.ok) {
        throw new Error(marketData.detail ?? "Unable to load market scan");
      }
      setUnusualRows(activityData.results ?? []);
      setMarketRows(marketData.results ?? []);
      await Promise.all([refreshHealth(), refreshHistory()]);
      const refreshedAt = Date.now();
      setLastUpdated(new Date(refreshedAt).toISOString());
      setRefreshStartedAt(refreshedAt);
      setRefreshDurationMs(refreshedAt - refreshStarted);
      setStatus("Ready");
    } catch (error) {
      setRefreshError(error.message);
      setStatus(error.message);
    } finally {
      setSignalRefreshing(false);
    }
  }

  function resetDashboardControls() {
    setExchange("Both");
    setLookback("5");
    setJump("1");
    setAutoRefresh(false);
    setView("price-pulse");
    setTableExchange("All");
    setSortKey("Symbol");
    setSortDirection("asc");
    setTableDensity("comfortable");
    setAutoRefreshInterval("60");
    setTableSearch("");
    clearDashboardPreferences();
    setStatus("Ready");
  }

  async function startScan() {
    setRows([]);
    setView("price-pulse");
    setStatus("Starting");
    try {
      const params = new URLSearchParams({
        exchange_category: exchange,
        lookback_minutes: lookback,
        jump_percent: jump,
      });
      const response = await fetch(
        `/api/v1/intraday/price-jumps/start?${params.toString()}`,
        { method: "POST" },
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to start scan");
      setJobId(data.job_id);
      setStatus("queued");
    } catch (error) {
      setStatus(error.message);
    }
  }

  useEffect(() => {
    if (!autoRefresh || jobId) {
      setNextAutoScanAt(null);
      setAutoRefreshCountdown(null);
      return undefined;
    }
    const intervalMs = Number.parseInt(autoRefreshInterval, 10) * 1000;
    const safeIntervalMs = Number.isFinite(intervalMs) && intervalMs >= 30000 ? intervalMs : 60000;
    const scheduleNext = () => setNextAutoScanAt(Date.now() + safeIntervalMs);
    scheduleNext();
    const timer = setInterval(() => {
      void startScan();
      scheduleNext();
    }, safeIntervalMs);
    return () => clearInterval(timer);
  }, [autoRefresh, autoRefreshInterval, jobId, exchange, lookback, jump]);

  useEffect(() => {
    if (!refreshStartedAt) {
      setRefreshAgeSeconds(null);
      return undefined;
    }
    const updateAge = () => {
      setRefreshAgeSeconds(Math.max(0, Math.floor((Date.now() - refreshStartedAt) / 1000)));
    };
    updateAge();
    const timer = setInterval(updateAge, 1000);
    return () => clearInterval(timer);
  }, [refreshStartedAt]);

  useEffect(() => {
    if (!nextAutoScanAt) return undefined;
    const timer = setInterval(() => {
      setAutoRefreshCountdown(Math.max(0, Math.ceil((nextAutoScanAt - Date.now()) / 1000)));
    }, 1000);
    return () => clearInterval(timer);
  }, [nextAutoScanAt]);

  const signalCount = rows.length + unusualRows.length + marketRows.length;
  const refreshAgeLabel = refreshAgeSeconds === null
    ? null
    : refreshAgeSeconds < 60
      ? `${refreshAgeSeconds}s ago`
      : refreshAgeSeconds < 3600
        ? `${Math.floor(refreshAgeSeconds / 60)}m ago`
        : `${Math.floor(refreshAgeSeconds / 3600)}h ago`;
  const healthStatus = systemHealth?.status ?? "checking";
  const pulseCount = rows.length;
  const unusualCount = unusualRows.length;
  const marketCount = marketRows.length;

  const { activeRows, visibleRows, signalCounts, sectorSummary } = useMemo(() => {
    const active = view === "price-pulse" ? rows : view === "unusual" ? unusualRows : marketRows;
    const visible = active
      .filter((row) => tableExchange === "All" || row.Exchange === tableExchange)
      .filter((row) => !tableSearch || String(row.Symbol ?? "").toLowerCase().includes(tableSearch.toLowerCase()))
      .slice()
      .sort((a, b) => {
        const left = a[sortKey] ?? "";
        const right = b[sortKey] ?? "";
        const numericLeft = Number.parseFloat(left);
        const numericRight = Number.parseFloat(right);
        const comparison = Number.isNaN(numericLeft) || Number.isNaN(numericRight)
          ? String(left).localeCompare(String(right))
          : numericLeft - numericRight;
        return sortDirection === "asc" ? comparison : -comparison;
      });

    const pulsePositive = signalCounts.pulsePositive;
    const pulseNegative = signalCounts.pulseNegative;
    const unusualPositive = signalCounts.unusualPositive;
    const unusualNegative = signalCounts.unusualNegative;
    const marketBullish = signalCounts.marketBullish;
    const marketBearish = signalCounts.marketBearish;

    const sectors = Object.values(
      marketRows.reduce((groups, row) => {
        const sector = row.Sector ?? "Unclassified";
        const current = groups[sector] ?? { sector, stocks: 0, bullish: 0, bearish: 0, scoreTotal: 0, scoreCount: 0 };
        const trend = String(row.Trend ?? "");
        const score = Number.parseFloat(row["AI Score"]);
        current.stocks += 1;
        if (/bull|up|positive|strong/i.test(trend)) current.bullish += 1;
        if (/bear|down|negative|weak/i.test(trend)) current.bearish += 1;
        if (!Number.isNaN(score)) {
          current.scoreTotal += score;
          current.scoreCount += 1;
        }
        groups[sector] = current;
        return groups;
      }, {}),
    )
      .map((item) => ({
        ...item,
        breadth: item.bullish - item.bearish,
        averageScore: item.scoreCount ? item.scoreTotal / item.scoreCount : null,
      }))
      .sort((a, b) => b.breadth - a.breadth || b.stocks - a.stocks);

    return {
      activeRows: active,
      visibleRows: visible,
      signalCounts: { pulsePositive, pulseNegative, unusualPositive, unusualNegative, marketBullish, marketBearish },
      sectorSummary: sectors,
    };
  }, [marketRows, rows, sortDirection, sortKey, tableExchange, tableSearch, unusualRows, view]);

  const expandedScan = useMemo(() => history.find((scan) => scan.job_id === expandedHistoryJob), [expandedHistoryJob, history]);
  const alerts = [];
  if (health === "offline") alerts.push({ level: "critical", text: "API connection is offline." });
  if (healthStatus === "STALE") alerts.push({ level: "warning", text: "Latest persisted scan is stale." });
  if (healthStatus === "NO_SCAN" || healthStatus === "EMPTY") alerts.push({ level: "warning", text: "No usable completed intraday scan is available." });
  if (status === "failed" || status === "API error") alerts.push({ level: "critical", text: `Scanner status: ${status}.` });
  if (pulsePositive > 0 && pulseNegative > 0) alerts.push({ level: "info", text: `Mixed price-pulse signals: ${pulsePositive} positive and ${pulseNegative} negative.` });
  if (!alerts.length) alerts.push({ level: "ok", text: "EROS dashboard systems are operating normally." });

  return (
    <div className="app">
      <header>
        <div>
          <p className="eyebrow">EROS · AI STOCK ANALYZER</p>
          <h1>Intraday Command Center</h1>
          <p className="subtitle">React frontend over the existing FastAPI scanner.</p>
        </div>
        <div className={`health ${health}`} role="status" aria-live="polite">● API {health}</div>
      </header>

      <main id="main-content" tabIndex="-1">
        <section className="panel alert-panel" aria-labelledby="alerts-heading">
          <div className="panel-title"><h2 id="alerts-heading">System alerts</h2><span>{alerts.length} active</span></div>
          <div className="alert-list">
            {alerts.map((alert, index) => (
              <div className={`alert alert-${alert.level}`} key={`${alert.level}-${index}`}>
                <strong>{alert.level.toUpperCase()}</strong>
                <span>{alert.text}</span>
              </div>
            ))}
          </div>
        </section>

        <div className="stats">
          <Stat label="Scanner" value={status} detail="Background job" />
          <Stat
            label="Data health"
            value={systemHealth?.status ?? "checking"}
            detail={systemHealth?.message ?? "Latest persisted scan"}
          />
          <Stat label="Candidates" value={rows.length || systemHealth?.candidates || "—"} detail="Latest pulse" />
          <Stat label="History" value={history.length} detail="Saved scans" />
          <Stat label="Mode" value="NSE + BSE" detail="Existing scanner universe" />
        </div>

        <section className="panel freshness-bar" aria-label="Dashboard data freshness">
          <div><span>Dashboard data</span><strong>{lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "Not refreshed yet"}</strong></div>
          <div><span>Auto-scan</span><strong>{autoRefresh ? "ON · 60s" : "OFF"}</strong></div>
          <div><span>API health</span><strong>{health}</strong></div>
        </section>

        {jobId ? (
          <section className="panel scan-progress" aria-label="Scan progress" role="status" aria-live="polite">
            <div className="panel-title"><h2>Scan in progress</h2><span>Job {jobId.slice(0, 10)}…</span></div>
            <div className="progress-track"><div className="progress-indeterminate" /></div>
            <p>Price-pulse scanner is running. Results will appear automatically when the job completes.</p>
          </section>
        ) : null}

        <section className="panel signal-strip" aria-label="Signal counts">
          <div><span>Pulse signals</span><strong>{pulseCount}</strong></div>
          <div><span>Unusual activity</span><strong>{unusualCount}</strong></div>
          <div><span>Market signals</span><strong>{marketCount}</strong></div>
          <div><span>Combined signals</span><strong>{signalCount}</strong></div>
          <div><span>System state</span><strong>{healthStatus}</strong></div>
        </section>

        <section className="panel signal-summary" aria-label="Signal direction summary">
          <div><span>Pulse positive</span><strong>{pulsePositive}</strong><small>of {pulseCount}</small></div>
          <div><span>Pulse negative</span><strong>{pulseNegative}</strong><small>of {pulseCount}</small></div>
          <div><span>Activity positive</span><strong>{unusualPositive}</strong><small>of {unusualCount}</small></div>
          <div><span>Activity negative</span><strong>{unusualNegative}</strong><small>of {unusualCount}</small></div>
          <div><span>Market bullish</span><strong>{marketBullish}</strong><small>of {marketCount}</small></div>
          <div><span>Market bearish</span><strong>{marketBearish}</strong><small>of {marketCount}</small></div>
        </section>

        <section className="panel sector-overview">
          <div className="panel-title">
            <h2>Sector overview</h2>
            <span>Derived from current market scanner results</span>
          </div>
          {sectorSummary.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Sector</th><th>Stocks</th><th>Bullish</th><th>Bearish</th><th>Breadth</th><th>Avg AI score</th></tr>
                </thead>
                <tbody>
                  {sectorSummary.map((item) => (
                    <tr key={item.sector}>
                      <td><strong>{item.sector}</strong></td>
                      <td>{item.stocks}</td>
                      <td>{item.bullish}</td>
                      <td>{item.bearish}</td>
                      <td>{item.breadth > 0 ? `+${item.breadth}` : item.breadth}</td>
                      <td>{item.averageScore === null ? "—" : item.averageScore.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">Refresh the market scanner to populate sector coverage.</p>
          )}
        </section>

        <section className="panel options-analytics" aria-labelledby="options-heading">
          <div className="panel-title">
            <div>
              <h2 id="options-heading">Options Analytics</h2>
              <span>NSE primary · Yahoo fallback</span>
            </div>
            <span>{optionsData?.status ?? "Not loaded"}</span>
          </div>

          <div className="controls options-controls">
            <div>
              <label htmlFor="options-underlying">Underlying</label>
              <select
                id="options-underlying"
                value={optionsUnderlying}
                onChange={(event) => {
                  setOptionsUnderlying(event.target.value);
                  setOptionsExpiry("");
                  setOptionsData(null);
                  setOptionsError(null);
                  setOptionsUpdatedAt(null);
                }}
              >
                <option value="NIFTY">NIFTY</option>
                <option value="BANKNIFTY">BANKNIFTY</option>
                <option value="FINNIFTY">FINNIFTY</option>
              </select>
            </div>
            <div>
              <label htmlFor="options-expiry">Expiry</label>
              <select
                id="options-expiry"
                value={optionsExpiry}
                onChange={(event) => setOptionsExpiry(event.target.value)}
                disabled={!optionsData?.expiries?.length || optionsLoading}
              >
                {!optionsData?.expiries?.length ? <option value="">Load chain first</option> : null}
                {optionsData?.expiries?.map((expiry) => (
                  <option key={expiry} value={expiry}>{expiry}</option>
                ))}
              </select>
            </div>
            <button onClick={() => loadOptionsChain()} disabled={optionsLoading}>
              {optionsLoading ? "Loading…" : "Load option chain"}
            </button>
          </div>

          {optionsError ? (
            <div className="stock-detail-error" role="alert">
              <strong>Unable to load options analytics</strong>
              <span>{optionsError}</span>
              <button className="secondary" onClick={() => loadOptionsChain()} disabled={optionsLoading}>
                Retry
              </button>
            </div>
          ) : optionsData?.status === "AVAILABLE" ? (
            <>
              <div className="options-meta" aria-label="Options analytics status">
                <div><span>Provider</span><strong>{optionsData.provider ?? "—"}</strong></div>
                <div><span>Spot</span><strong>{optionsData.spot ?? "—"}</strong></div>
                <div><span>Expiry</span><strong>{optionsData.expiry ?? "—"}</strong></div>
                <div><span>Contracts</span><strong>{optionsData.count ?? 0}</strong></div>
                <div><span>Updated</span><strong>{optionsUpdatedAt ? new Date(optionsUpdatedAt).toLocaleTimeString() : "—"}</strong></div>
              </div>

              <div className="options-summary">
                {(optionsData.summary ?? []).map((item) => (
                  <div key={item.Metric}>
                    <span>{item.Metric}</span>
                    <strong>{item.Value ?? "—"}</strong>
                  </div>
                ))}
              </div>

              <div className="table-wrap options-table">
                <table>
                  <thead>
                    <tr>
                      <th>Strike</th>
                      <th>CE LTP</th>
                      <th>CE OI</th>
                      <th>CE OI Δ</th>
                      <th>CE IV</th>
                      <th>PE LTP</th>
                      <th>PE OI</th>
                      <th>PE OI Δ</th>
                      <th>PE IV</th>
                      <th>PCR OI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(optionsData.chain ?? []).map((row, index) => (
                      <tr key={`${row.strike ?? "strike"}-${index}`}>
                        <td><strong>{row.strike ?? "—"}</strong></td>
                        <td>{row["CE LTP"] ?? "—"}</td>
                        <td>{row["CE OI"] ?? "—"}</td>
                        <td>{row["CE OI change"] ?? "—"}</td>
                        <td>{row["CE IV"] ?? "—"}</td>
                        <td>{row["PE LTP"] ?? "—"}</td>
                        <td>{row["PE OI"] ?? "—"}</td>
                        <td>{row["PE OI change"] ?? "—"}</td>
                        <td>{row["PE IV"] ?? "—"}</td>
                        <td>{row["PCR OI"] ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="empty">Select an index and load its current option chain.</p>
          )}
        </section>

        <section className="panel view-tabs" aria-label="Dashboard result views">
          <div className="view-tab-group" role="tablist" aria-label="Signal result views">
            <span className="shortcut-help" role="note">
              Shortcuts: 1/2/3 views · F search · E export · R refresh · Esc clear
            </span>
            <button
              role="tab"
              aria-selected={view === "price-pulse"}
              className={view === "price-pulse" ? "active" : "secondary"}
              onClick={() => setView("price-pulse")}
            >
              Price pulse
            </button>
            <button
              role="tab"
              aria-selected={view === "unusual"}
              className={view === "unusual" ? "active" : "secondary"}
              onClick={() => setView("unusual")}
            >
              Unusual activity
            </button>
            <button
              role="tab"
              aria-selected={view === "market"}
              className={view === "market" ? "active" : "secondary"}
              onClick={() => setView("market")}
            >
              Market scanner
            </button>
          </div>
        </section>

        <section className="panel controls">
          <div>
            <label htmlFor="exchange-select">Exchange</label>
            <select id="exchange-select" value={exchange} onChange={(e) => setExchange(e.target.value)}>
              <option>Both</option><option>NSE</option><option>BSE</option>
            </select>
          </div>
          <div>
            <label htmlFor="lookback-select">Lookback</label>
            <select id="lookback-select" value={lookback} onChange={(e) => setLookback(e.target.value)}>
              <option value="5">5 min</option><option value="10">10 min</option><option value="15">15 min</option>
            </select>
          </div>
          <div>
            <label htmlFor="jump-select">Jump threshold</label>
            <select id="jump-select" value={jump} onChange={(e) => setJump(e.target.value)}>
              <option value="1">1%</option><option value="2">2%</option><option value="3">3%</option>
            </select>
          </div>
          <button onClick={startScan} disabled={Boolean(jobId)}>
            {jobId ? "Scanning…" : "Start price-pulse scan"}
          </button>
          <button
            className={autoRefresh ? "active" : "secondary"}
            onClick={() => setAutoRefresh((enabled) => !enabled)}
            aria-pressed={autoRefresh}
          >
            {autoRefresh ? "Auto-scan: ON" : "Auto-scan: OFF"}
          </button>
          <div>
            <label htmlFor="auto-refresh-interval">Auto-scan interval</label>
            <select
              id="auto-refresh-interval"
              value={autoRefreshInterval}
              onChange={(e) => setAutoRefreshInterval(e.target.value)}
              disabled={autoRefresh}
            >
              <option value="30">30 sec</option>
              <option value="60">60 sec</option>
              <option value="120">2 min</option>
              <option value="300">5 min</option>
            </select>
          </div>
          {autoRefresh && autoRefreshCountdown !== null ? (
            <span className="refresh-status" role="status" aria-live="polite">
              Next auto-scan in {autoRefreshCountdown}s
            </span>
          ) : null}
          <button className="secondary" onClick={loadUnusualActivity}>
            Unusual activity
          </button>
          <button className="secondary" onClick={loadMarketScanner}>
            Market scanner
          </button>
          <button className="secondary" onClick={exportVisibleRows} disabled={!visibleRows.length} aria-label="Export visible results as CSV">
            Export CSV
          </button>
          <button
            className="secondary"
            onClick={refreshSignalBoard}
            disabled={signalRefreshing}
            aria-busy={signalRefreshing}
            aria-label={
              signalRefreshing
                ? "Refreshing all signals"
                : refreshError
                  ? "Retry failed signal refresh"
                  : "Refresh all signals"
            }
            title="Refresh activity, market signals, health, and history. Keyboard shortcut: R"
          >
            {signalRefreshing ? "Refreshing…" : refreshError ? "Retry refresh" : "Refresh all signals"}{!signalRefreshing ? " (R)" : ""}
          </button>
          {signalRefreshing ? (
            <span className="refresh-status" role="status" aria-live="polite" aria-busy="true">
              Updating activity, market signals, health, and history…
            </span>
          ) : refreshError ? (
            <span className="refresh-status" role="alert">
              Last refresh failed: {refreshError}
              <button className="secondary refresh-retry" onClick={refreshSignalBoard} disabled={signalRefreshing}>
                Retry refresh
              </button>
            </span>
          ) : refreshStartedAt ? (
            <span className="refresh-status" role="status" aria-live="polite">
              Last refresh completed at {new Date(refreshStartedAt).toLocaleTimeString()}{refreshDurationMs !== null ? ` · took ${(refreshDurationMs / 1000).toFixed(1)}s` : ""}{refreshAgeLabel ? (
                <span aria-hidden="true" title="Time since the latest completed refresh">{` · ${refreshAgeLabel}`}</span>
              ) : null}
            </span>
          ) : (
            <span className="refresh-status" role="status" aria-live="polite">
              Refresh ready · no refresh run yet
            </span>
          )}
          <button className="secondary" onClick={refreshHistory} aria-label="Refresh saved scan history">Refresh history</button>
          <button className="secondary" onClick={resetDashboardControls} aria-label="Reset dashboard filters and controls">
            Reset controls
          </button>
        </section>

        <section className="panel">
          <div className="panel-title">
            <div className="panel-heading">
              <h2>{view === "unusual" ? "Unusual activity" : view === "market" ? "Market scanner" : "Latest price pulses"}</h2>
              <span className="view-badge" role="status" aria-live="polite">
                {view === "unusual" ? "Activity view" : view === "market" ? "Market view" : "Pulse view"}
              </span>
            </div>
            <span>
              {view === "unusual" ? unusualRows.length : view === "market" ? marketRows.length : rows.length} results
              {lastUpdated ? ` · updated ${new Date(lastUpdated).toLocaleTimeString()}` : ""}
            </span>
          </div>
          <div className="table-toolbar">
            <label htmlFor="stock-search">Search symbol</label>
            <input id="stock-search" type="search" value={tableSearch} onChange={(e) => setTableSearch(e.target.value)} placeholder="e.g. RELIANCE" aria-label="Search visible stocks by symbol" />
            {tableSearch ? (
              <button className="secondary clear-search" onClick={() => setTableSearch("")} aria-label="Clear stock search">
                Clear
              </button>
            ) : null}
            <label htmlFor="table-exchange">Table exchange</label>
            <select id="table-exchange" value={tableExchange} onChange={(e) => setTableExchange(e.target.value)}>
              <option>All</option><option>NSE</option><option>BSE</option>
            </select>
            <label htmlFor="table-density">Density</label>
            <select id="table-density" value={tableDensity} onChange={(e) => setTableDensity(e.target.value)}>
              <option value="comfortable">Comfortable</option><option value="compact">Compact</option>
            </select>
            <span role="status" aria-live="polite">
              {visibleRows.length} visible of {activeRows.length} · sorted by {sortKey} ({sortDirection === "asc" ? "ascending" : "descending"})
              {tableSearch ? ` · filtered by "${tableSearch}"` : ""}
              {status !== "Ready" ? ` · status: ${status}` : ""}
            </span>
          </div>
          <div className={`table-wrap table-density-${tableDensity}`}>
            {view === "price-pulse" ? (
              <table>
                <thead><tr><SortHeader label="Symbol" column="Symbol" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><th>Exchange</th><SortHeader label="Last price" column="Last price" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Change" column="Change over 5m" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Volume" column="Volume vs recent bars" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /></tr></thead>
                <tbody>
                  {visibleRows.length ? visibleRows.map((row, i) => (
                    <tr key={row.Symbol ?? i}>
                      <td><button className="stock-link" onClick={() => loadStockDetail(row.Symbol, row.Exchange)}>{row.Symbol ?? "—"}</button></td>
                      <td>{row.Exchange ?? "—"}</td>
                      <td>{row["Last price"] ?? "—"}</td>
                      <td>{row["Change over 5m"] ?? "—"}</td>
                      <td>{row["Volume vs recent bars"] ?? "—"}</td>
                    </tr>
                  )) : <tr><td colSpan="5"><div className="empty-state"><strong>No price-pulse candidates</strong><span>{tableSearch ? `No symbols match "${tableSearch}".` : "Run a scan to populate live candidates."}</span><button className="secondary" onClick={startScan} disabled={Boolean(jobId)}>{jobId ? "Scanning…" : "Start scan"}</button></div></td></tr>}
                </tbody>
              </table>
            ) : view === "unusual" ? (
              <table>
                <thead><tr><SortHeader label="Symbol" column="Symbol" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><th>Exchange</th><SortHeader label="Signal" column="Signal" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Price" column="Price" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Volume" column="Volume ratio" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /></tr></thead>
                <tbody>
                  {visibleRows.length ? visibleRows.map((row, i) => (
                    <tr key={row.Symbol ?? i}>
                      <td><button className="stock-link" onClick={() => loadStockDetail(row.Symbol, row.Exchange)}>{row.Symbol ?? "—"}</button></td>
                      <td>{row.Exchange ?? "—"}</td>
                      <td>{row.Signal ?? row["Activity signal"] ?? "—"}</td>
                      <td>{row.Price ?? row["Last price"] ?? "—"}</td>
                      <td>{row["Volume ratio"] ?? row["Volume vs recent bars"] ?? "—"}</td>
                    </tr>
                  )) : <tr><td colSpan="5"><div className="empty-state"><strong>No unusual activity</strong><span>{tableSearch ? `No symbols match "${tableSearch}".` : "Refresh the signal board to check the latest activity."}</span><button className="secondary" onClick={loadUnusualActivity}>Refresh activity</button></div></td></tr>}
                </tbody>
              </table>
            ) : (
              <table>
                <thead><tr><SortHeader label="Symbol" column="Symbol" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Price" column="Price" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="Trend" column="Trend" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><SortHeader label="RSI" column="RSI" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /><th>MACD</th><SortHeader label="AI score" column="AI Score" sortKey={sortKey} sortDirection={sortDirection} onSort={changeSort} /></tr></thead>
                <tbody>
                  {visibleRows.length ? visibleRows.map((row, i) => (
                    <tr key={row.Symbol ?? i}>
                      <td><button className="stock-link" onClick={() => loadStockDetail(row.Symbol, row.Exchange)}>{row.Symbol ?? "—"}</button></td>
                      <td>{row.Price ?? "—"}</td>
                      <td>{row.Trend ?? "—"}</td>
                      <td>{row.RSI ?? "—"}</td>
                      <td>{row.MACD ?? "—"}</td>
                      <td>{row["AI Score"] ?? row.AI_Score ?? "—"}</td>
                    </tr>
                  )) : <tr><td colSpan="6"><div className="empty-state"><strong>No market scanner results</strong><span>{tableSearch ? `No symbols match "${tableSearch}".` : "Load the market scanner to populate the table."}</span><button className="secondary" onClick={loadMarketScanner}>Load market scanner</button></div></td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </section>

        {selectedStock ? (
          <section className="panel" aria-labelledby="stock-detail-heading">
            <div className="panel-title">
              <h2 id="stock-detail-heading">
                {selectedStock.symbol} · {selectedStock.exchange} drill-down
              </h2>
              <div className="stock-detail-actions">
                <button
                  className="secondary"
                  onClick={() => loadStockDetail(selectedStock.symbol, selectedStock.exchange)}
                  disabled={stockDetailLoading}
                  aria-label="Refresh stock drill-down"
                >
                  {stockDetailLoading ? "Refreshing…" : "Refresh"}
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    setSelectedStock(null);
                    setStockDetail(null);
                    setStockDetailError(null);
                    setStockDetailUpdatedAt(null);
                  }}
                  aria-label="Close stock drill-down"
                >
                  Close
                </button>
              </div>
            </div>
            {stockDetailLoading ? (
              <p className="empty" role="status" aria-live="polite">Loading stock detail…</p>
            ) : stockDetailError ? (
              <div className="stock-detail-error" role="alert">
                <strong>Unable to load stock detail</strong>
                <span>{stockDetailError}</span>
                <button
                  className="secondary"
                  onClick={() => loadStockDetail(selectedStock.symbol, selectedStock.exchange)}
                >
                  Retry
                </button>
              </div>
            ) : stockDetail ? (
              <>
                <div className="stock-detail-grid">
                  <div><span>Price</span><strong>{stockDetail.price ?? "—"}</strong></div>
                  <div><span>Trend</span><strong>{stockDetail.trend ?? "—"}</strong></div>
                  <div><span>Signal</span><strong>{stockDetail.signal ?? "—"}</strong></div>
                  <div><span>Breakout</span><strong>{stockDetail.breakout ?? "—"}</strong></div>
                  {Object.entries(stockDetail.metrics ?? {}).map(([key, value]) => (
                    <div key={key}>
                      <span>{key}</span>
                      <strong>{value ?? "—"}</strong>
                    </div>
                  ))}
                </div>
                {stockDetailUpdatedAt ? <p className="stock-detail-updated">Updated {new Date(stockDetailUpdatedAt).toLocaleTimeString()}</p> : null}
                <p className="stock-observation">
                  {stockDetail.market_observation ?? "No additional market observation."}
                </p>
                <div className="stock-detail-meta" aria-label="Stock detail context">
                  <span>Source: existing analyzer</span>
                  <span>Exchange: {selectedStock.exchange}</span>
                  {stockDetailUpdatedAt ? <span>Updated: {new Date(stockDetailUpdatedAt).toLocaleTimeString()}</span> : null}
                </div>
                <StockChart points={stockDetail.chart} />
              </>
            ) : (
              <p className="empty">Unable to load stock detail.</p>
            )}
          </section>
        ) : null}

        <section className="panel">
          <div className="panel-title"><h2>Exchange health</h2><span>{systemHealth?.completed_at ?? "No completed scan"}</span></div>
          <div className="table-wrap">
            {systemHealth?.exchanges?.length ? (
              <table>
                <thead><tr><th>Exchange</th><th>Candidates</th><th>Avg change</th><th>Avg volume surge</th><th>Positive change</th></tr></thead>
                <tbody>
                  {systemHealth.exchanges.map((item) => (
                    <tr key={item.Exchange}>
                      <td><strong>{item.Exchange}</strong></td>
                      <td>{item.Candidates ?? "—"}</td>
                      <td>{item["Average change %"] ?? "—"}</td>
                      <td>{item["Average volume surge x"] ?? "—"}</td>
                      <td>{item["Positive change %"] ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="empty">Run a price-pulse scan to populate exchange health.</p>}
          </div>
        </section>

        <section className="panel">
          <div className="panel-title"><h2>Recent scan history</h2><span>Last 10 · click a scan to inspect</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Completed</th><th>Job</th><th>Candidates</th><th>Universe checked</th></tr></thead>
              <tbody>
                {history.length ? history.map((scan) => (
                  <tr key={scan.job_id} className={expandedHistoryJob === scan.job_id ? "history-row-active" : ""}>
                    <td>{scan.completed_at ?? "—"}</td>
                    <td><button className="stock-link" onClick={() => setExpandedHistoryJob((current) => current === scan.job_id ? null : scan.job_id)}>{scan.job_id?.slice(0, 10) ?? "—"}…</button></td>
                    <td>{scan.count ?? "—"}</td>
                    <td>{scan.scan_stats?.candidate_count ?? "—"}</td>
                  </tr>
                )) : <tr><td colSpan="4" className="empty">No saved scans yet.</td></tr>}
              </tbody>
            </table>
          </div>
          {expandedScan ? (
            <div className="history-detail">
              <div className="panel-title">
                <strong>Saved scan candidates · {(expandedScan.results ?? []).length} total</strong>
                <div className="history-detail-actions">
                  <span>{expandedScan.completed_at ?? "—"}</span>
                  <button
                    className="secondary"
                    onClick={() => setExpandedHistoryJob(null)}
                    aria-label="Close saved scan details"
                  >
                    Close
                  </button>
                </div>
              </div>
              <div className="history-preview-label">
                Showing {(expandedScan.results ?? []).slice(0, 10).length} of {(expandedScan.results ?? []).length} candidates
              </div>
              <div className="history-candidates">
                {(expandedScan.results ?? []).slice(0, 10).map((row, index) => (
                  <button
                    className="history-candidate"
                    key={`${row.Symbol ?? "row"}-${index}`}
                    onClick={() => loadStockDetail(row.Symbol, row.Exchange)}
                  >
                    <strong>{row.Symbol ?? "—"}</strong>
                    <span>{row.Exchange ?? "—"} · {row["Change over 5m"] ?? "—"}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}

export default App;
