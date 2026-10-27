/**
 * NexusTrade AI - Modern SPA Desktop Trading Controller
 * 4 Dedicated Views: Chart (Diagram), Trade (Live Results), History, Settings
 * Styled with MetaTrader 5 Mobile Aesthetics & Lightweight-Charts
 */

document.addEventListener("DOMContentLoaded", () => {
  // --- Header Action Elements ---
  const btnToggleBot = document.getElementById("btn-toggle-bot");
  const btnCurrencyToggle = document.getElementById("btn-currency-toggle");
  const currToggleFlag = document.getElementById("curr-toggle-flag");
  const currToggleText = document.getElementById("curr-toggle-text");
  const cfgDisplayCurrency = document.getElementById("cfg-display-currency");
  const cfgIdrRate = document.getElementById("cfg-idr-rate");

  let displayCurrency = localStorage.getItem("nexus_display_currency") || "IDR";
  let savedRate = parseFloat(localStorage.getItem("nexus_idr_rate"));
  // If user previously had old 16000 default or invalid, upgrade to real live rate baseline
  let idrExchangeRate = (savedRate && savedRate > 1000 && savedRate !== 16000) ? savedRate : 18090;

  function updateCurrencyButton() {
    if (currToggleFlag && currToggleText) {
      if (displayCurrency === "IDR") {
        currToggleFlag.textContent = "IDR";
        currToggleText.textContent = "Rp";
      } else {
        currToggleFlag.textContent = "USD";
        currToggleText.textContent = "$";
      }
    }
    if (heroCurrencyLabel) {
      heroCurrencyLabel.textContent = displayCurrency === "IDR" ? "Mata Uang: IDR (Rp)" : "Mata Uang: USD ($)";
    }
    if (cfgDisplayCurrency) cfgDisplayCurrency.value = displayCurrency;
    if (cfgIdrRate) cfgIdrRate.value = idrExchangeRate;
  }

  async function fetchLiveUsdIdrRate(showToastOnDone = false) {
    try {
      const res = await fetch("/api/currency/usd-idr");
      const data = await res.json();
      if (data.success && data.rate) {
        idrExchangeRate = Math.round(data.rate);
        localStorage.setItem("nexus_idr_rate", idrExchangeRate);
        if (cfgIdrRate) cfgIdrRate.value = idrExchangeRate;
        const badge = document.getElementById("rate-live-badge");
        if (badge) {
          badge.innerHTML = `<span class="pulse-dot"></span> Live: Rp ${idrExchangeRate.toLocaleString("id-ID")}`;
        }
        updateCurrencyButton();
        fetchStatus();
        fetchPositions();
        fetchHistoryPage();
        if (showToastOnDone) {
          showToast(`Kurs pasar USD/IDR berhasil disinkronkan: Rp ${idrExchangeRate.toLocaleString("id-ID")}`, "success");
        }
      }
    } catch (e) {
      console.error("fetchLiveUsdIdrRate error", e);
    }
  }

  const btnSyncLiveRate = document.getElementById("btn-sync-live-rate");
  if (btnSyncLiveRate) {
    btnSyncLiveRate.addEventListener("click", () => fetchLiveUsdIdrRate(true));
  }

  if (cfgIdrRate) {
    cfgIdrRate.addEventListener("input", () => {
      const v = parseFloat(cfgIdrRate.value);
      if (v > 1000) {
        idrExchangeRate = v;
        localStorage.setItem("nexus_idr_rate", idrExchangeRate);
        const badge = document.getElementById("rate-live-badge");
        if (badge) badge.textContent = "Custom";
        updateCurrencyButton();
        fetchStatus();
        fetchPositions();
        fetchHistoryPage();
      }
    });
  }

  const mt5StatusPill = document.getElementById("mt5-status-pill");
  const mt5StatusDot = document.getElementById("mt5-status-dot");
  const mt5StatusText = document.getElementById("mt5-status-text");
  const antiSleepPill = document.getElementById("anti-sleep-pill");
  const antiSleepDot = document.getElementById("anti-sleep-dot");
  const circuitBreakerText = document.getElementById("circuit-breaker-text");
  const btnResetDdHeader = document.getElementById("btn-reset-dd-header");
  const btnResetDdSettings = document.getElementById("btn-reset-drawdown-settings");

  // Chart View Header Telemetry
  const valBalance = document.getElementById("val-balance");
  const valServer = document.getElementById("val-server");
  const valEquity = document.getElementById("val-equity");
  const valFloatingProfit = document.getElementById("val-floating-profit");
  const valFreeMargin = document.getElementById("val-free-margin");
  const valMarginLevel = document.getElementById("val-margin-level");
  const valTradeMode = document.getElementById("val-trade-mode");
  const valTimeframe = document.getElementById("val-timeframe");

  // Chart Legend Elements
  const legOpen = document.getElementById("leg-open");
  const legHigh = document.getElementById("leg-high");
  const legLow = document.getElementById("leg-low");
  const legClose = document.getElementById("leg-close");

  // Trade View Telemetry (Matching MT5 Mobile Screenshot)
  const tradeViewAccLogin = document.getElementById("trade-view-acc-login");
  const tradeValSaldo = document.getElementById("trade-val-saldo");
  const tradeValEquity = document.getElementById("trade-val-equity");
  const tradeValMargin = document.getElementById("trade-val-margin");
  const tradeValMarginBebas = document.getElementById("trade-val-margin-bebas");
  const tradeValLevelMargin = document.getElementById("trade-val-level-margin");
  const tradeValFloating = document.getElementById("trade-val-floating");
  const tradePosCountTag = document.getElementById("trade-pos-count-tag");
  const mt5PositionsContainer = document.getElementById("mt5-positions-container");
  const btnTradeFlatAll = document.getElementById("btn-trade-flat-all");
  const btnRefreshPositions = document.getElementById("btn-refresh-positions");

  // Bottom Navigation & Dock
  const navBtnHome = document.getElementById("nav-btn-home");
  const navBtnChart = document.getElementById("nav-btn-chart");
  const navBtnTrade = document.getElementById("nav-btn-trade");
  const navBtnHistory = document.getElementById("nav-btn-history");
  const navBtnSettings = document.getElementById("nav-btn-settings");
  const navTradeBadge = document.getElementById("nav-trade-badge");
  const btnDockQuickFab = document.getElementById("btn-dock-quick-fab");

  // Hero Portfolio Action Pills (Screen 2)
  const btnHeroCurrencySwitch = document.getElementById("btn-hero-currency-switch");
  const heroCurrencyLabel = document.getElementById("hero-currency-label");
  const btnHeroBotAction = document.getElementById("btn-hero-bot-action");
  const heroBotLabel = document.getElementById("hero-bot-label");
  const valPnlPct = document.getElementById("val-pnl-pct");
  const headerUserAccount = document.getElementById("header-user-account");

  // Screen 1 Welcome Modal
  const welcomeModal = document.getElementById("welcome-modal");
  const btnWelcomeStart = document.getElementById("btn-welcome-start");
  const btnWelcomeLogin = document.getElementById("btn-welcome-login");
  const btnOpenProfileCard = document.getElementById("btn-open-profile-card");

  // Screen 3 Detail & Chart Hero Elements
  const chartActivePairName = document.getElementById("chart-active-pair-name");
  const chartHeroPrice = document.getElementById("chart-hero-price");
  const chartHeroChange = document.getElementById("chart-hero-change");

  // History View Elements
  const histTotalPnl = document.getElementById("hist-total-pnl");
  const histTotalDeals = document.getElementById("hist-total-deals");
  const histWinLossRatio = document.getElementById("hist-winloss-ratio");
  const histWinrate = document.getElementById("hist-winrate");
  const pageHistoryTbody = document.getElementById("page-history-tbody");
  const btnRefreshHistory = document.getElementById("btn-refresh-history");

  // Settings View Elements
  const formPageSettings = document.getElementById("form-page-settings");
  const btnSavePageSettingsTop = document.getElementById("btn-save-page-settings-top");

  // Containers
  const signalsContainer = document.getElementById("signals-container");
  const toastContainer = document.getElementById("toast-container");
  const chartContainer = document.getElementById("tv-chart-container");

  // Modals for Secondary Operations
  const modalBacktest = document.getElementById("modal-backtest");
  const modalLicense = document.getElementById("modal-license");

  // Chart State
  let currentActiveView = localStorage.getItem("nexus_active_view") || "home";
  let selectedSymbol = localStorage.getItem("nexus_selected_symbol") || "EURUSD";
  let selectedTimeframe = localStorage.getItem("nexus_selected_tf") || "M15";
  let chart = null;
  let candlestickSeries = null;
  let volumeSeries = null;
  let emaSeries = null;
  let activePriceLines = [];

  let botIsRunning = false;
  let currentMinScore = 3;
  let accountCurrency = "$";

  // Dynamic Symbol Price Precision helper
  function getSymbolPrecision(symbol) {
    if (symbol.includes("XAU") || symbol.includes("GOLD") || symbol.includes("JPY")) {
      return { precision: 2, minMove: 0.01 };
    }
    return { precision: 5, minMove: 0.00001 };
  }

  function formatPrice(val, symbol) {
    if (val === undefined || val === null || isNaN(val)) return "-";
    const prec = getSymbolPrecision(symbol).precision;
    return Number(val).toFixed(prec);
  }

  function formatMoney(amount, options = {}) {
    if (amount === undefined || amount === null || isNaN(amount)) return "0";
    const num = Number(amount);
    const withSign = options.withSign || false;
    const includeUnit = options.includeUnit !== undefined ? options.includeUnit : true;

    if (displayCurrency === "IDR") {
      const idrVal = Math.round(num * idrExchangeRate);
      const absVal = Math.abs(idrVal);
      const signStr = withSign ? (idrVal >= 0 ? "+" : "-") : (idrVal < 0 ? "-" : "");
      const unit = includeUnit ? "Rp " : "";
      return `${signStr}${unit}${absVal.toLocaleString("id-ID")}`;
    } else {
      const absVal = Math.abs(num);
      const signStr = withSign ? (num >= 0 ? "+" : "-") : (num < 0 ? "-" : "");
      const unit = includeUnit ? "$" : "";
      return `${signStr}${unit}${absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
  }

  // Toast Notification (100% Vector SVG Icons)
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = "toast-msg";
    
    let iconSvg = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px; color: var(--accent-cyan); flex-shrink: 0;">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
    `;
    if (type === "success") {
      iconSvg = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px; color: var(--accent-green); flex-shrink: 0;">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      `;
    } else if (type === "error") {
      iconSvg = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px; color: var(--accent-red); flex-shrink: 0;">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
      `;
    } else if (type === "warning") {
      iconSvg = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 16px; height: 16px; color: var(--accent-amber); flex-shrink: 0;">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      `;
    }

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    if (toastContainer) {
      toastContainer.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(8px)";
        setTimeout(() => toast.remove(), 260);
      }, 3500);
    }
  }

  // =========================================================================
  // SPA VIEW SWITCHER (HOME, CHART, TRADE, HISTORY, SETTINGS)
  // =========================================================================
  function switchView(viewName) {
    currentActiveView = viewName;
    localStorage.setItem("nexus_active_view", viewName);

    // Toggle views
    document.querySelectorAll(".app-view").forEach((v) => {
      v.classList.remove("active");
      v.style.display = "none";
    });

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
      targetView.style.display = "flex";
      targetView.classList.add("active");
    }

    // Toggle bottom dock items
    document.querySelectorAll(".dock-item, .bottom-nav-item").forEach((b) => b.classList.remove("active"));
    const activeNavBtn = document.getElementById(`nav-btn-${viewName}`);
    if (activeNavBtn) activeNavBtn.classList.add("active");

    // Action per view switch
    if (viewName === "home") {
      fetchStatus();
      fetchSignals();
      fetchLiveTick();
    } else if (viewName === "chart") {
      if (chart && chartContainer) {
        setTimeout(() => {
          const w = chartContainer.clientWidth || 1100;
          const h = getResponsiveChartHeight();
          chart.applyOptions({ width: w, height: h });
          chart.timeScale().fitContent();
        }, 80);
      }
      fetchChartData();
      fetchLiveTick();
    } else if (viewName === "trade") {
      fetchStatus();
      fetchPositions();
    } else if (viewName === "history") {
      fetchHistoryPage();
    } else if (viewName === "settings") {
      loadSettingsIntoPageForm();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Nav Button Click Handlers
  if (navBtnHome) navBtnHome.addEventListener("click", () => switchView("home"));
  if (navBtnChart) navBtnChart.addEventListener("click", () => switchView("chart"));
  if (navBtnTrade) navBtnTrade.addEventListener("click", () => switchView("trade"));
  if (navBtnHistory) navBtnHistory.addEventListener("click", () => switchView("history"));
  if (navBtnSettings) navBtnSettings.addEventListener("click", () => switchView("settings"));

  // Signature Center Floating Action Button (⇄)
  if (btnDockQuickFab) {
    btnDockQuickFab.addEventListener("click", () => {
      if (currentActiveView === "home") {
        switchView("chart");
      } else {
        switchView("home");
      }
    });
  }

  const btnChartBackHome = document.getElementById("btn-chart-back-home");
  if (btnChartBackHome) {
    btnChartBackHome.addEventListener("click", () => switchView("home"));
  }

  // Currency Switcher Toggle Handler
  function toggleCurrency() {
    displayCurrency = displayCurrency === "IDR" ? "USD" : "IDR";
    localStorage.setItem("nexus_display_currency", displayCurrency);
    updateCurrencyButton();
    const msg =
      displayCurrency === "IDR"
        ? `Mata uang tampilan diubah ke Rupiah (Kurs: 1 USD = Rp ${idrExchangeRate.toLocaleString("id-ID")})`
        : "Mata uang tampilan diubah ke US Dollar ($)";
    showToast(msg, "info");
    fetchStatus();
    fetchPositions();
    fetchHistoryPage();
  }

  if (btnCurrencyToggle) btnCurrencyToggle.addEventListener("click", toggleCurrency);
  if (btnHeroCurrencySwitch) btnHeroCurrencySwitch.addEventListener("click", toggleCurrency);

  // Screen 1 Welcome Modal Handlers
  if (btnWelcomeStart) {
    btnWelcomeStart.addEventListener("click", () => {
      if (welcomeModal) welcomeModal.classList.remove("active");
      localStorage.setItem("nexus_has_seen_intro", "true");
    });
  }
  if (btnWelcomeLogin) {
    btnWelcomeLogin.addEventListener("click", () => {
      if (welcomeModal) welcomeModal.classList.remove("active");
      localStorage.setItem("nexus_has_seen_intro", "true");
      switchView("settings");
    });
  }
  if (btnOpenProfileCard) {
    btnOpenProfileCard.addEventListener("click", () => {
      if (welcomeModal) welcomeModal.classList.add("active");
    });
  }

  function getResponsiveChartHeight() {
    if (window.innerWidth <= 380) return 270;
    if (window.innerWidth <= 480) return 300;
    if (window.innerWidth <= 768) return 330;
    if (window.innerWidth <= 992) return 380;
    return 440;
  }

  // =========================================================================
  // TRADINGVIEW LIGHTWEIGHT CHARTS INITIALIZATION
  // =========================================================================
  function initChart() {
    if (!window.LightweightCharts || !chartContainer) {
      console.warn("LightweightCharts library or container not ready.");
      return;
    }

    const { createChart } = window.LightweightCharts;
    const containerWidth = chartContainer.clientWidth || 1100;
    const containerHeight = getResponsiveChartHeight();

    chart = createChart(chartContainer, {
      width: containerWidth,
      height: containerHeight,
      layout: {
        background: { color: "transparent" },
        textColor: "#7a7f8f",
        fontFamily: "'JetBrains Mono', -apple-system, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.025)" },
        horzLines: { color: "rgba(255, 255, 255, 0.025)" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: "rgba(255, 85, 0, 0.4)",
          width: 1,
          style: 3,
          labelBackgroundColor: "#14151b",
        },
        horzLine: {
          color: "rgba(255, 85, 0, 0.4)",
          width: 1,
          style: 3,
          labelBackgroundColor: "#14151b",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.06)",
        scaleMargins: {
          top: 0.1,
          bottom: 0.22,
        },
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.06)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const initialFmt = getSymbolPrecision(selectedSymbol);

    // 1. Candlestick Series (Shakuro Emerald & Crimson)
    candlestickSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      priceFormat: {
        type: "price",
        precision: initialFmt.precision,
        minMove: initialFmt.minMove,
      },
    });

    // 2. Volume Series (Isolated Overlay Pane)
    volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
      visible: false,
    });

    // 3. EMA 50 Trend Line
    emaSeries = chart.addLineSeries({
      color: "#06b6d4",
      lineWidth: 2,
      crosshairMarkerVisible: true,
      priceLineVisible: false,
      priceFormat: {
        type: "price",
        precision: initialFmt.precision,
        minMove: initialFmt.minMove,
      },
    });

    // Crosshair hover updater
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData.get(candlestickSeries)) {
        return;
      }
      const data = param.seriesData.get(candlestickSeries);
      if (data) {
        const dec = getSymbolPrecision(selectedSymbol).precision;
        if (legOpen) legOpen.textContent = data.open.toFixed(dec);
        if (legHigh) legHigh.textContent = data.high.toFixed(dec);
        if (legLow) legLow.textContent = data.low.toFixed(dec);
        if (legClose) legClose.textContent = data.close.toFixed(dec);
      }
    });

    // Responsive window auto-resize
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length && chart && currentActiveView === "chart") {
        const { width } = entries[0].contentRect;
        const h = getResponsiveChartHeight();
        if (width > 0) chart.applyOptions({ width, height: h });
      }
    });
    resizeObserver.observe(chartContainer);

    fetchChartData();
  }

  // --- Fetch & Render Chart Data ---
  async function fetchChartData() {
    if (!chart || !candlestickSeries) return;

    try {
      const res = await fetch(`/api/chart?symbol=${selectedSymbol}&timeframe=${selectedTimeframe}&count=160`);
      const data = await res.json();

      if (data.candles && data.candles.length > 0) {
        // 1. Remove previous price lines FIRST so old price levels don't distort vertical auto-scale
        activePriceLines.forEach((line) => {
          try {
            candlestickSeries.removePriceLine(line);
          } catch (e) {}
        });
        activePriceLines = [];

        const { precision, minMove } = getSymbolPrecision(selectedSymbol);
        candlestickSeries.applyOptions({
          priceFormat: {
            type: "price",
            precision: precision,
            minMove: minMove,
          },
        });
        if (emaSeries) {
          emaSeries.applyOptions({
            priceFormat: {
              type: "price",
              precision: precision,
              minMove: minMove,
            },
          });
        }

        candlestickSeries.setData(data.candles);

        const lastBar = data.candles[data.candles.length - 1];
        if (legOpen) legOpen.textContent = lastBar.open.toFixed(precision);
        if (legHigh) legHigh.textContent = lastBar.high.toFixed(precision);
        if (legLow) legLow.textContent = lastBar.low.toFixed(precision);
        if (legClose) legClose.textContent = lastBar.close.toFixed(precision);

        if (data.volume && volumeSeries) {
          volumeSeries.setData(data.volume);
        }

        if (data.ema && emaSeries) {
          emaSeries.setData(data.ema);
        }

        if (data.markers) {
          candlestickSeries.setMarkers(data.markers);
        }

        if (data.support) {
          const supLine = candlestickSeries.createPriceLine({
            price: data.support,
            color: "#10b981",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "SUPPORT",
          });
          activePriceLines.push(supLine);
        }

        if (data.resistance) {
          const resLine = candlestickSeries.createPriceLine({
            price: data.resistance,
            color: "#f43f5e",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: "RESISTANCE",
          });
          activePriceLines.push(resLine);
        }

        if (data.active_positions && data.active_positions.length > 0) {
          data.active_positions.forEach((pos) => {
            const entryLine = candlestickSeries.createPriceLine({
              price: pos.price_open,
              color: "#38bdf8",
              lineWidth: 2,
              lineStyle: 3,
              axisLabelVisible: true,
              title: `ENTRY #${pos.ticket}`,
            });
            activePriceLines.push(entryLine);

            if (pos.sl > 0) {
              const slLine = candlestickSeries.createPriceLine({
                price: pos.sl,
                color: "#ef4444",
                lineWidth: 2,
                lineStyle: 0,
                axisLabelVisible: true,
                title: `HARD SL #${pos.ticket}`,
              });
              activePriceLines.push(slLine);
            }
          });
        }

        if (data.current_tick) {
          updateQuickTradeBar(data.current_tick);
        }
      }
    } catch (e) {
      console.error("fetchChartData error", e);
    }
  }

  // Chart Controls & Live Sync with Bot Engine
  const chartSyncSummary = document.getElementById("chart-sync-summary");
  const settingsSyncPairs = document.getElementById("settings-sync-pairs");
  const settingsSyncTf = document.getElementById("settings-sync-tf");

  function updateSyncBadges(symbols, timeframe) {
    let symText = "EURUSD";
    if (Array.isArray(symbols)) {
      if (symbols.length === 3) symText = "Semua Pair (3)";
      else if (symbols.length > 0) symText = symbols.join(", ");
    } else if (typeof symbols === "string") {
      symText = symbols;
    }
    const tfText = timeframe || selectedTimeframe || "M15";

    if (chartSyncSummary) chartSyncSummary.textContent = `${symText} (${tfText})`;
    if (settingsSyncPairs) settingsSyncPairs.textContent = symText;
    if (settingsSyncTf) settingsSyncTf.textContent = tfText;
  }

  async function quickSyncTrading(payload) {
    try {
      const res = await fetch("/api/trading/quick-sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        updateSyncBadges(data.symbols, data.timeframe);
        fetchSignals();
        const elSumTf = document.getElementById("settings-summary-tf");
        if (elSumTf) elSumTf.textContent = `Timeframe: ${data.timeframe}`;
        const elSumSymbols = document.getElementById("settings-summary-symbols");
        if (elSumSymbols) elSumSymbols.textContent = `${(data.symbols || []).length} Pairs`;
      }
    } catch (e) {
      console.error("quickSync error", e);
    }
  }

  const symbolSelector = document.getElementById("chart-symbol-selector");
  if (symbolSelector) {
    symbolSelector.addEventListener("click", async (e) => {
      const btn = e.target.closest(".symbol-btn");
      if (!btn) return;
      document.querySelectorAll(".symbol-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const sym = btn.dataset.symbol;
      let activeSymbols = [];
      if (sym === "ALL") {
        activeSymbols = ["EURUSD", "GBPUSD", "XAUUSD"];
        showToast("Bot disinkronkan: Memantau & tradingkan SEMUA 3 Pair!", "success");
      } else {
        activeSymbols = [sym];
        selectedSymbol = sym;
        localStorage.setItem("nexus_selected_symbol", selectedSymbol);
        showToast(`Bot disinkronkan: Fokus HANYA trading pada pair ${sym}!`, "success");
      }

      await quickSyncTrading({ symbols: activeSymbols });
      fetchLiveTick();
      fetchChartData();
      if (chart) chart.timeScale().fitContent();
    });
  }

  const tfSelector = document.getElementById("chart-tf-selector");
  if (tfSelector) {
    tfSelector.addEventListener("click", async (e) => {
      const btn = e.target.closest(".tf-btn");
      if (!btn) return;
      document.querySelectorAll(".tf-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      selectedTimeframe = btn.dataset.tf;
      localStorage.setItem("nexus_selected_tf", selectedTimeframe);
      showToast(`Timeframe bot disinkronkan ke: ${selectedTimeframe}`, "info");

      await quickSyncTrading({ timeframe: selectedTimeframe });
      fetchChartData();
      if (chart) chart.timeScale().fitContent();
    });
  }

  const btnToggleVol = document.getElementById("btn-toggle-vol");
  let isVolVisible = true;
  if (btnToggleVol) {
    btnToggleVol.addEventListener("click", () => {
      isVolVisible = !isVolVisible;
      const volLabel = document.getElementById("vol-toggle-label");
      if (volLabel) {
        volLabel.textContent = isVolVisible ? "Vol: ON" : "Vol: OFF";
      } else {
        btnToggleVol.textContent = isVolVisible ? "Vol: ON" : "Vol: OFF";
      }
      btnToggleVol.style.opacity = isVolVisible ? "1" : "0.5";
      if (volumeSeries) volumeSeries.applyOptions({ visible: isVolVisible });
    });
  }

  // =========================================================================
  // ONE-CLICK QUICK TRADE BAR (METATRADER 5 MOBILE STYLE)
  // =========================================================================
  const btnQuickSell = document.getElementById("btn-quick-sell");
  const btnQuickBuy = document.getElementById("btn-quick-buy");
  const qtBidPrice = document.getElementById("qt-bid-price");
  const qtAskPrice = document.getElementById("qt-ask-price");
  const qtSpreadVal = document.getElementById("qt-spread-val");
  const qtLotInput = document.getElementById("qt-lot-input");
  const btnQtLotMinus = document.getElementById("btn-qt-lot-minus");
  const btnQtLotPlus = document.getElementById("btn-qt-lot-plus");
  const qtActiveSymbolLabel = document.getElementById("qt-active-symbol-label");

  // Restore saved quick lot
  if (qtLotInput) {
    const savedLot = localStorage.getItem("nexus_quick_lot");
    if (savedLot) qtLotInput.value = savedLot;

    qtLotInput.addEventListener("change", () => {
      let val = parseFloat(qtLotInput.value) || 0.01;
      val = Math.max(0.01, Math.min(10.0, val));
      qtLotInput.value = val.toFixed(2);
      localStorage.setItem("nexus_quick_lot", val.toFixed(2));
    });
  }

  if (btnQtLotMinus && qtLotInput) {
    btnQtLotMinus.addEventListener("click", () => {
      let val = parseFloat(qtLotInput.value) || 0.01;
      val = Math.max(0.01, parseFloat((val - 0.01).toFixed(2)));
      qtLotInput.value = val.toFixed(2);
      localStorage.setItem("nexus_quick_lot", val.toFixed(2));
    });
  }

  if (btnQtLotPlus && qtLotInput) {
    btnQtLotPlus.addEventListener("click", () => {
      let val = parseFloat(qtLotInput.value) || 0.01;
      val = parseFloat((val + 0.01).toFixed(2));
      qtLotInput.value = val.toFixed(2);
      localStorage.setItem("nexus_quick_lot", val.toFixed(2));
    });
  }

  function updateQuickTradeBar(tick) {
    if (!tick) return;
    const currentSym = selectedSymbol || "EURUSD";
    if (qtActiveSymbolLabel) qtActiveSymbolLabel.textContent = currentSym;
    if (chartActivePairName) chartActivePairName.textContent = currentSym;

    const formattedBid = formatPrice(tick.bid, currentSym);
    const formattedAsk = formatPrice(tick.ask, currentSym);

    if (tick.bid !== undefined) {
      if (qtBidPrice) qtBidPrice.textContent = formattedBid;
      if (chartHeroPrice) chartHeroPrice.textContent = formattedBid;

      const elFund = document.getElementById(`fund-price-${currentSym.toLowerCase()}`);
      if (elFund) elFund.textContent = formattedBid;
      const elWl = document.getElementById(`wl-price-${currentSym.toLowerCase()}`);
      if (elWl) elWl.textContent = formattedBid;
    }
    if (tick.ask !== undefined && qtAskPrice) {
      qtAskPrice.textContent = formattedAsk;
    }
    if (qtSpreadVal && (tick.spread !== undefined || tick.spread_points !== undefined)) {
      const sp = tick.spread !== undefined ? tick.spread : tick.spread_points;
      qtSpreadVal.textContent = `${sp} pts`;
      if (chartHeroChange) {
        chartHeroChange.innerHTML = `<span class="change-delta">Spread: ${sp} pts</span> <span class="change-pct positive">LIVE TICK</span>`;
      }
    }
  }

  async function fetchLiveTick() {
    try {
      const res = await fetch(`/api/trading/tick?symbol=${selectedSymbol}`);
      const data = await res.json();
      if (data.success) {
        updateQuickTradeBar(data);
      }
    } catch (e) {
      // silent fallback
    }
  }

  async function executeQuickOrder(action) {
    const lot = parseFloat(qtLotInput ? qtLotInput.value : 0.01) || 0.01;
    const sym = selectedSymbol || "EURUSD";

    // Visual loading state
    if (btnQuickSell) btnQuickSell.disabled = true;
    if (btnQuickBuy) btnQuickBuy.disabled = true;

    try {
      const res = await fetch("/api/trading/manual-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: sym, action: action, lot: lot })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showToast(data.message || `Posisi ${action} ${lot} ${sym} berhasil dibuka!`, "success");
        fetchPositions();
        fetchStatus();
        fetchChartData();
        fetchHistoryPage();
      } else {
        const errMsg = data.detail || data.error || "Gagal membuka order di MT5.";
        showToast(`Gagal Order: ${errMsg}`, "error");
      }
    } catch (e) {
      showToast(`Kesalahan jaringan: ${e}`, "error");
    } finally {
      if (btnQuickSell) btnQuickSell.disabled = false;
      if (btnQuickBuy) btnQuickBuy.disabled = false;
    }
  }

  if (btnQuickSell) {
    btnQuickSell.addEventListener("click", () => executeQuickOrder("SELL"));
  }

  if (btnQuickBuy) {
    btnQuickBuy.addEventListener("click", () => executeQuickOrder("BUY"));
  }

  // =========================================================================
  // TELEMETRY & ACCOUNT POLLING
  // =========================================================================
  async function fetchStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();

      botIsRunning = data.bot_running;
      btnToggleBot.className = botIsRunning ? "pill-btn-action paused" : "pill-btn-action";
      if (botIsRunning) {
        btnToggleBot.innerHTML = `
          <span class="bot-status-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" style="width: 12px; height: 12px;">
              <rect x="6" y="4" width="4" height="16"></rect>
              <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
          </span>
          <span class="bot-btn-label">Pause Bot</span>
        `;
      } else {
        btnToggleBot.innerHTML = `
          <span class="bot-status-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" style="width: 12px; height: 12px;">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          </span>
          <span class="bot-btn-label">Start Bot</span>
        `;
      }

      if (heroBotLabel) {
        heroBotLabel.textContent = botIsRunning ? "Pause Bot Engine" : "Start Bot Engine";
      }
      if (btnHeroBotAction) {
        btnHeroBotAction.style.borderColor = botIsRunning ? "rgba(239, 68, 68, 0.5)" : "var(--border-hairline)";
      }

      const headerAvatarDot = document.getElementById("header-avatar-dot");
      if (headerAvatarDot) {
        headerAvatarDot.className = data.mt5_connected ? "avatar-pulse-dot" : "avatar-pulse-dot offline";
      }

      if (data.mt5_connected) {
        mt5StatusDot.className = "pulse-dot";
        if (data.account && data.account.trade_allowed === false) {
          mt5StatusText.innerHTML = `MT5: #${data.account.login || "Connected"} <span style="color: var(--accent-amber); font-weight:700;">(Algo Trading OFF)</span>`;
          if (mt5StatusPill) mt5StatusPill.title = "Tombol 'Algo Trading' di aplikasi MetaTrader 5 sedang NONAKTIF (Merah). Klik tombol Algo Trading di toolbar MT5 agar order dapat dieksekusi.";
        } else {
          mt5StatusText.textContent = `MT5: #${data.account?.login || "Connected"}`;
          if (mt5StatusPill) mt5StatusPill.title = "Koneksi MetaTrader 5 Aktif & Siap Eksekusi";
        }
        valServer.textContent = `Server: ${data.account?.server || "Connected"}`;

        if (headerUserAccount) {
          headerUserAccount.textContent = `MT5 #${data.account?.login || "Live"} • ${data.account?.server || "Server"}`;
        }

        const bal = data.account.balance || 0;
        const eq = data.account.equity || 0;
        const profit = data.account.profit || 0;
        const margin = data.account.margin || 0;
        const freeMargin = data.account.margin_free || 0;
        const marginLevel = data.account.margin_level || 0;

        // Chart & Hero Telemetry
        valBalance.textContent = formatMoney(bal);
        valEquity.textContent = formatMoney(eq);
        valFloatingProfit.textContent = `Floating: ${formatMoney(profit, { withSign: true })}`;
        valFloatingProfit.style.color = profit >= 0 ? "var(--accent-green)" : "var(--accent-red)";

        if (valPnlPct && bal > 0) {
          const pct = ((profit / bal) * 100).toFixed(2);
          const sign = profit >= 0 ? "+" : "";
          valPnlPct.textContent = `${sign}${pct}%`;
          valPnlPct.className = profit >= 0 ? "pnl-percent" : "pnl-percent negative";
          valPnlPct.style.color = profit >= 0 ? "var(--accent-green)" : "var(--accent-red)";
          valPnlPct.style.background = profit >= 0 ? "var(--accent-green-bg)" : "var(--accent-red-bg)";
        }

        valFreeMargin.textContent = formatMoney(freeMargin);
        valMarginLevel.textContent = `Margin Level: ${marginLevel.toFixed(1)}%`;
        const isReal = (data.account.trade_mode === "REAL");
        valTradeMode.textContent = data.account.trade_mode || "DEMO";
        valTradeMode.style.color = isReal ? "var(--accent-amber)" : "var(--accent-cyan)";

        // Trade View Telemetry (Exact MT5 Mobile Representation)
        if (tradeViewAccLogin) {
          tradeViewAccLogin.innerHTML = `Login: #${data.account.login || "MT5"} <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: ${isReal ? 'rgba(245,158,11,0.2)' : 'rgba(6,182,212,0.2)'}; color: ${isReal ? 'var(--accent-amber)' : 'var(--accent-cyan)'}; font-weight: 700;">${data.account.trade_mode || 'DEMO'}</span>`;
        }

        // Settings View Active Account Badge
        const settingsActiveAccountBadge = document.getElementById("settings-active-account-badge");
        if (settingsActiveAccountBadge) {
          settingsActiveAccountBadge.textContent = `Login: #${data.account.login || "--"} | Server: ${data.account.server || "--"}`;
        }
        const settingsActiveStatusIndicator = document.getElementById("settings-active-status-indicator");
        if (settingsActiveStatusIndicator) {
          settingsActiveStatusIndicator.textContent = isReal ? "REAL LIVE AKUN" : "DEMO SIMULASI";
          settingsActiveStatusIndicator.style.background = isReal ? "rgba(245, 158, 11, 0.2)" : "rgba(6, 182, 212, 0.15)";
          settingsActiveStatusIndicator.style.color = isReal ? "var(--accent-amber)" : "var(--accent-cyan)";
          settingsActiveStatusIndicator.style.borderColor = isReal ? "var(--accent-amber)" : "rgba(6, 182, 212, 0.3)";
        }
        const settingsActiveModeTag = document.getElementById("settings-active-account-mode-tag");
        if (settingsActiveModeTag) {
          settingsActiveModeTag.textContent = isReal ? "Live Mode" : "Demo Mode";
          settingsActiveModeTag.style.borderColor = isReal ? "var(--accent-amber)" : "rgba(6, 182, 212, 0.3)";
          settingsActiveModeTag.style.color = isReal ? "var(--accent-amber)" : "var(--accent-cyan)";
        }
        const elSumMode = document.getElementById("settings-summary-mode");
        if (elSumMode) {
          elSumMode.textContent = data.account.trade_mode || "DEMO";
          elSumMode.style.color = isReal ? "var(--accent-amber)" : "var(--accent-cyan)";
        }
        if (tradeValSaldo) tradeValSaldo.textContent = formatMoney(bal, { includeUnit: displayCurrency === "IDR" });
        if (tradeValEquity) tradeValEquity.textContent = formatMoney(eq, { includeUnit: displayCurrency === "IDR" });
        if (tradeValMargin) tradeValMargin.textContent = formatMoney(margin, { includeUnit: displayCurrency === "IDR" });
        if (tradeValMarginBebas) tradeValMarginBebas.textContent = formatMoney(freeMargin, { includeUnit: displayCurrency === "IDR" });
        if (tradeValLevelMargin) tradeValLevelMargin.textContent = `${marginLevel.toFixed(2)}%`;

        if (tradeValFloating) {
          tradeValFloating.textContent = formatMoney(profit, { withSign: true, includeUnit: displayCurrency === "IDR" });
          tradeValFloating.style.color = profit >= 0 ? "#38bdf8" : "var(--accent-red)";
        }
      } else {
        mt5StatusDot.className = "pulse-dot offline";
        mt5StatusText.textContent = "MT5: Disconnected";
        valServer.textContent = "Open MT5 & Enable Algo Trading";
      }

      valTimeframe.textContent = `Timeframe: ${data.timeframe}`;

      if (data.anti_sleep_active) {
        antiSleepDot.className = "pulse-dot";
        antiSleepText.textContent = "Anti-Sleep: Active";
      } else {
        antiSleepDot.className = "pulse-dot offline";
        antiSleepText.textContent = "Anti-Sleep: Idle";
      }

      if (data.drawdown.is_frozen) {
        circuitBreakerText.textContent = "Drawdown: FROZEN";
        circuitBreakerText.style.color = "var(--accent-red)";
        if (btnResetDdHeader) btnResetDdHeader.style.display = "inline-block";
      } else {
        const ddLimit = data.drawdown.max_allowed_pct > 0 ? `${data.drawdown.max_allowed_pct}%` : "Bebas/Off";
        circuitBreakerText.textContent = `Drawdown: Safe (Max: ${ddLimit})`;
        circuitBreakerText.style.color = "var(--accent-green)";
        if (btnResetDdHeader) btnResetDdHeader.style.display = "none";
      }
    } catch (e) {
      console.error("fetchStatus error", e);
    }
  }

  async function resetDailyDrawdown() {
    try {
      const res = await fetch("/api/drawdown/reset", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast("Proteksi harian berhasil di-reset. Bot dapat dijalankan kembali.", "success");
        fetchStatus();
      } else {
        showToast("Gagal me-reset proteksi harian.", "error");
      }
    } catch (e) {
      showToast(`Error: ${e}`, "error");
    }
  }

  if (btnResetDdHeader) btnResetDdHeader.addEventListener("click", resetDailyDrawdown);
  if (btnResetDdSettings) btnResetDdSettings.addEventListener("click", resetDailyDrawdown);

  // =========================================================================
  // TRADE POSITIONS (EXACT MT5 MOBILE STYLING FROM USER IMAGE)
  // =========================================================================
  window.closePositionManual = async function (ticket) {
    if (!confirm(`Tutup posisi order #${ticket} sekarang?`)) return;
    try {
      const res = await fetch(`/api/positions/${ticket}/close`, { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast(`Posisi #${ticket} berhasil ditutup!`, "success");
        fetchPositions();
        fetchStatus();
        fetchHistoryPage();
      } else {
        showToast(`Gagal menutup posisi #${ticket}.`, "error");
      }
    } catch (err) {
      showToast(`Error closing position: ${err}`, "error");
    }
  };

  async function fetchPositions() {
    try {
      const res = await fetch("/api/positions");
      const data = await res.json();
      const positions = data.positions || [];

      // Update Bottom Nav Badge
      if (navTradeBadge) {
        if (positions.length > 0) {
          navTradeBadge.style.display = "inline-block";
          navTradeBadge.textContent = positions.length;
        } else {
          navTradeBadge.style.display = "none";
        }
      }

      // Update Header Tag in Trade Page
      if (tradePosCountTag) {
        tradePosCountTag.textContent = `${positions.length} Posisi`;
      }

      if (!mt5PositionsContainer) return;

      if (positions.length === 0) {
        const statusMsg = botIsRunning
          ? "Bot aktif dan sedang memantau peluang konfluensi untuk entri otomatis."
          : "Bot sedang jeda (Paused). Klik tombol Start Bot di atas untuk mengaktifkan trading otomatis.";

        mt5PositionsContainer.innerHTML = `
          <div class="empty-state-card">
            <div class="empty-icon-svg">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
                <polyline points="16 7 22 7 22 13"></polyline>
              </svg>
            </div>
            <div class="empty-text">Tidak ada posisi terbuka saat ini.</div>
            <div class="empty-subtext">${statusMsg}</div>
          </div>
        `;
        return;
      }

      // Render positions vertically stacked exactly like the user's MT5 Mobile Reel screenshot!
      mt5PositionsContainer.innerHTML = positions
        .map((p) => {
          const isProfit = p.profit >= 0;
          const profitClass = isProfit ? "positive" : "negative";
          const formattedProfit = formatMoney(p.profit, { withSign: false, includeUnit: displayCurrency === "IDR" });
          const typeClass = p.type.toLowerCase();

          return `
          <div class="mt5-pos-row">
            <div class="mt5-pos-left">
              <div class="mt5-pos-symbol-line">
                <span class="mt5-pos-symbol">${p.symbol},</span>
                <span class="mt5-pos-type ${typeClass}">${typeClass} ${p.volume.toFixed(2)}</span>
              </div>
              <div class="mt5-pos-prices">
                <span>${formatPrice(p.price_open, p.symbol)}</span>
                <span class="mt5-arrow">→</span>
                <span>${formatPrice(p.price_current, p.symbol)}</span>
              </div>
              <div class="mt5-pos-subinfo">
                <span>SL: ${p.sl > 0 ? formatPrice(p.sl, p.symbol) : "HARD SL"}</span>
                <span>•</span>
                <span>Ticket: #${p.ticket}</span>
              </div>
            </div>

            <div class="mt5-pos-right">
              <div class="mt5-profit-big ${profitClass}">
                ${formattedProfit}
              </div>
            </div>
          </div>
        `;
        })
        .join("");
    } catch (e) {
      console.error("fetchPositions error", e);
    }
  }

  // Trade Page Controls
  if (btnRefreshPositions) {
    btnRefreshPositions.addEventListener("click", () => {
      fetchPositions();
      fetchStatus();
      showToast("Data posisi diperbarui.", "info");
    });
  }

  if (btnTradeFlatAll) {
    btnTradeFlatAll.addEventListener("click", async () => {
      if (!confirm("PERINGATAN: Tutup SEMUA posisi terbuka sekarang juga (Flat All)?")) return;
      const res = await fetch("/api/bot/flat", { method: "POST" });
      const data = await res.json();
      showToast(`Berhasil menutup ${data.closed_tickets.length} posisi terbuka.`, "warning");
      fetchPositions();
      fetchStatus();
      fetchHistoryPage();
      fetchChartData();
    });
  }

  // =========================================================================
  // CONFLUENCE RADAR (3-FACTOR AI SCANNER)
  // =========================================================================
  async function fetchSignals() {
    try {
      const res = await fetch("/api/signals");
      const data = await res.json();
      const signals = data.signals || [];

      if (signals.length === 0 || !signalsContainer) return;

      if (signals[0] && signals[0].target_score) {
        currentMinScore = signals[0].target_score;
      }

      signalsContainer.innerHTML = signals
        .map((s) => {
          let badgeClass = "signal-badge hold";
          if (s.action === "BUY") badgeClass = "signal-badge buy";
          if (s.action === "SELL") badgeClass = "signal-badge sell";

          const tagStructure = s.structure_aligned ? "factor-tag active" : "factor-tag";
          const tagSMC = s.smc_aligned ? "factor-tag active" : "factor-tag";
          const tagEMA = s.ema_trend_aligned ? "factor-tag active" : "factor-tag";

          const structText =
            s.structure_aligned && s.structure_bias === "RANGING" ? "S/R Test" : s.structure_bias;

          return `
          <div class="signal-card">
            <div class="signal-top">
              <span class="signal-pair">${s.symbol}</span>
              <span class="${badgeClass}">${s.action} (${s.confluence_score}/${s.target_score || 3})</span>
            </div>
            <div class="confluence-factors">
              <span class="${tagStructure}">Structure: ${structText}</span>
              <span class="${tagSMC}">SMC / Vol: ${s.has_ob ? "OB Hit" : s.has_volume_anomaly ? "Vol Spike" : "None"}</span>
              <span class="${tagEMA}">EMA Filter: ${s.ema_trend_aligned ? "Aligned" : "Opposite"}</span>
            </div>
            <div class="signal-rationale">${s.rationale}</div>
          </div>
        `;
        })
        .join("");
    } catch (e) {
      console.error("fetchSignals error", e);
    }
  }

  // =========================================================================
  // HISTORY PAGE (RIWAYAT TRANSAKSI DITUTUP)
  // =========================================================================
  async function fetchHistoryPage() {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      const deals = data.history || [];

      if (!pageHistoryTbody) return;

      if (deals.length === 0) {
        pageHistoryTbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-dim); padding: 35px 0;">
              Belum ada riwayat transaksi yang ditutup pada akun ini.
            </td>
          </tr>
        `;
        if (histTotalPnl) histTotalPnl.textContent = "$0.00";
        if (histTotalDeals) histTotalDeals.textContent = "0 Deals";
        if (histWinLossRatio) histWinLossRatio.textContent = "0 Menang / 0 Kalah";
        if (histWinrate) histWinrate.textContent = "0%";
        return;
      }

      let totalPnl = 0;
      let wins = 0;
      let losses = 0;

      deals.forEach((d) => {
        totalPnl += d.profit || 0;
        if (d.profit > 0) wins++;
        else if (d.profit < 0) losses++;
      });

      const totalTradesCount = wins + losses;
      const winratePct = totalTradesCount > 0 ? ((wins / totalTradesCount) * 100).toFixed(1) : 0;

      if (histTotalPnl) {
        histTotalPnl.textContent = formatMoney(totalPnl, { withSign: true });
        histTotalPnl.style.color = totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";
      }
      if (histTotalDeals) histTotalDeals.textContent = `${deals.length} Deals`;
      if (histWinLossRatio) histWinLossRatio.textContent = `${wins} Menang / ${losses} Kalah`;
      if (histWinrate) histWinrate.textContent = `${winratePct}%`;

      pageHistoryTbody.innerHTML = deals
        .map((d) => {
          const isProf = d.profit >= 0;
          const pClass = isProf ? "profit-plus" : "profit-minus";
          const typeBadge = d.type === "BUY" ? "signal-badge buy" : "signal-badge sell";
          const dateStr = d.time ? new Date(d.time * 1000).toLocaleString() : "-";

          return `
          <tr>
            <td>#${d.ticket}</td>
            <td><b>${d.symbol}</b></td>
            <td><span class="${typeBadge}">${d.type}</span></td>
            <td>${d.volume.toFixed(2)}</td>
            <td>${formatPrice(d.price, d.symbol)}</td>
            <td class="${pClass}">${formatMoney(d.profit, { withSign: true })}</td>
            <td style="color: var(--text-dim); font-size: 0.8rem;">${dateStr}</td>
          </tr>
        `;
        })
        .join("");
    } catch (e) {
      console.error("fetchHistoryPage error", e);
    }
  }

  if (btnRefreshHistory) {
    btnRefreshHistory.addEventListener("click", () => {
      fetchHistoryPage();
      showToast("Riwayat transaksi diperbarui.", "info");
    });
  }

  // =========================================================================
  // SETTINGS VIEW (IN-PAGE FORM, BUKAN POPUP/MODAL)
  // =========================================================================
  async function loadSettingsIntoPageForm() {
    try {
      const res = await fetch("/api/config");
      const cfg = await res.json();

      const elFixedLot = document.getElementById("cfg-page-fixed-lot");
      if (elFixedLot) elFixedLot.value = cfg.risk.fixed_lot_size;

      const elRiskPct = document.getElementById("cfg-page-risk-pct");
      if (elRiskPct) elRiskPct.value = cfg.risk.risk_per_trade_percent;

      const elMaxDd = document.getElementById("cfg-page-max-dd");
      if (elMaxDd) elMaxDd.value = cfg.risk.max_daily_drawdown_percent;

      const elMaxPos = document.getElementById("cfg-page-max-pos");
      if (elMaxPos) elMaxPos.value = cfg.risk.max_open_positions;

      const elMaxLayers = document.getElementById("cfg-page-max-layers");
      if (elMaxLayers) elMaxLayers.value = cfg.risk.max_layers_per_symbol || 3;

      if (cfg.confluence) {
        const minConfEl = document.getElementById("cfg-page-min-confluence");
        if (minConfEl) minConfEl.value = cfg.confluence.min_confluence_score || 3;

        const emaEl = document.getElementById("cfg-page-ema-period");
        if (emaEl) emaEl.value = cfg.confluence.ema_trend_period || 50;

        const volEl = document.getElementById("cfg-page-vol-multiplier");
        if (volEl) volEl.value = cfg.confluence.volume_spike_multiplier || 1.8;

        const swingEl = document.getElementById("cfg-page-swing-lookback");
        if (swingEl) swingEl.value = cfg.confluence.swing_lookback_bars || 10;
      }

      // Populate MT5 Account inputs if available
      if (cfg.mt5) {
        const elMt5Acc = document.getElementById("cfg-mt5-account");
        if (elMt5Acc && (!elMt5Acc.value || elMt5Acc.value === "0")) {
          elMt5Acc.value = cfg.mt5.account || "";
        }
        const elMt5Srv = document.getElementById("cfg-mt5-server");
        if (elMt5Srv && !elMt5Srv.value) {
          elMt5Srv.value = cfg.mt5.server || "MetaQuotes-Demo";
        }
      }

      // Update Top Metrics Strip in Settings Page
      const elSumMode = document.getElementById("settings-summary-mode");
      if (elSumMode) elSumMode.textContent = (cfg.system.mode || "demo").toUpperCase();

      const elSumTf = document.getElementById("settings-summary-tf");
      if (elSumTf) elSumTf.textContent = `Timeframe: ${cfg.trading.timeframe || "M15"}`;

      const elSumSymbols = document.getElementById("settings-summary-symbols");
      if (elSumSymbols) elSumSymbols.textContent = `${(cfg.trading.symbols || []).length} Pairs`;

      const elSumLot = document.getElementById("settings-summary-lot");
      if (elSumLot) elSumLot.textContent = `${cfg.risk.fixed_lot_size} Lot / ${cfg.risk.risk_per_trade_percent}%`;

      const elSumDd = document.getElementById("settings-summary-dd");
      if (elSumDd) elSumDd.textContent = `Max DD: ${cfg.risk.max_daily_drawdown_percent}%`;

      const elSumScore = document.getElementById("settings-summary-score");
      if (elSumScore) {
        const score = cfg.confluence?.min_confluence_score || 3;
        elSumScore.textContent = `${score} / 3 Factors`;
      }

      // Synchronize Chart Active Buttons with Loaded Config
      if (cfg.trading) {
        updateSyncBadges(cfg.trading.symbols, cfg.trading.timeframe);

        const syms = cfg.trading.symbols || [];
        const savedSym = localStorage.getItem("nexus_selected_symbol");

        if (syms.length === 1) {
          selectedSymbol = syms[0];
          localStorage.setItem("nexus_selected_symbol", selectedSymbol);
        } else if (savedSym && (syms.includes(savedSym) || syms.length === 0)) {
          selectedSymbol = savedSym;
        } else if (syms.length > 1) {
          selectedSymbol = syms[0];
        }

        const curTf = cfg.trading.timeframe || "M15";
        selectedTimeframe = curTf;
        localStorage.setItem("nexus_selected_tf", selectedTimeframe);

        // Highlight matching symbol button
        document.querySelectorAll(".symbol-btn").forEach((b) => {
          b.classList.remove("active");
          if (syms.length > 1 && b.dataset.symbol === "ALL") {
            b.classList.add("active");
          } else if (b.dataset.symbol === selectedSymbol) {
            b.classList.add("active");
          }
        });

        // Highlight matching timeframe button
        document.querySelectorAll(".tf-btn").forEach((b) => {
          b.classList.remove("active");
          if (b.dataset.tf === curTf) b.classList.add("active");
        });

        fetchLiveTick();
        fetchChartData();
      }

      updateCurrencyButton();
    } catch (e) {
      console.error("loadSettingsIntoPageForm error", e);
    }
  }

  async function savePageSettings(e) {
    if (e) e.preventDefault();

    try {
      const resCfg = await fetch("/api/config");
      const cfg = await resCfg.json();

      const elFixedLot = document.getElementById("cfg-page-fixed-lot");
      if (elFixedLot) cfg.risk.fixed_lot_size = parseFloat(elFixedLot.value);

      const elRiskPct = document.getElementById("cfg-page-risk-pct");
      if (elRiskPct) cfg.risk.risk_per_trade_percent = parseFloat(elRiskPct.value);

      const elMaxDd = document.getElementById("cfg-page-max-dd");
      if (elMaxDd) cfg.risk.max_daily_drawdown_percent = parseFloat(elMaxDd.value);

      const elMaxPos = document.getElementById("cfg-page-max-pos");
      if (elMaxPos) cfg.risk.max_open_positions = parseInt(elMaxPos.value);

      const elMaxLayers = document.getElementById("cfg-page-max-layers");
      if (elMaxLayers) cfg.risk.max_layers_per_symbol = parseInt(elMaxLayers.value);

      if (!cfg.confluence) cfg.confluence = {};
      const elMinConf = document.getElementById("cfg-page-min-confluence");
      if (elMinConf) cfg.confluence.min_confluence_score = parseInt(elMinConf.value);

      const elEma = document.getElementById("cfg-page-ema-period");
      if (elEma) cfg.confluence.ema_trend_period = parseInt(elEma.value);

      const elVol = document.getElementById("cfg-page-vol-multiplier");
      if (elVol) cfg.confluence.volume_spike_multiplier = parseFloat(elVol.value);

      const elSwing = document.getElementById("cfg-page-swing-lookback");
      if (elSwing) cfg.confluence.swing_lookback_bars = parseInt(elSwing.value);

      if (cfgDisplayCurrency) {
        displayCurrency = cfgDisplayCurrency.value;
        localStorage.setItem("nexus_display_currency", displayCurrency);
      }
      if (cfgIdrRate) {
        idrExchangeRate = parseFloat(cfgIdrRate.value) || 16000;
        localStorage.setItem("nexus_idr_rate", idrExchangeRate);
      }
      updateCurrencyButton();

      const saveRes = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });

      if (saveRes.ok) {
        showToast("Pengaturan berhasil disimpan dan langsung diterapkan!", "success");
        loadSettingsIntoPageForm();
        fetchStatus();
        fetchPositions();
        fetchHistoryPage();
        fetchSignals();
        fetchChartData();
      } else {
        const err = await saveRes.json();
        showToast(`Gagal menyimpan pengaturan: ${err.detail}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err}`, "error");
    }
  }

  if (formPageSettings) formPageSettings.addEventListener("submit", savePageSettings);

  if (btnSavePageSettingsTop) {
    btnSavePageSettingsTop.addEventListener("click", (e) => savePageSettings(e));
  }
  const btnSavePageSettingsBottom = document.getElementById("btn-save-page-settings-bottom");
  if (btnSavePageSettingsBottom) {
    btnSavePageSettingsBottom.addEventListener("click", (e) => savePageSettings(e));
  }

  const btnSwitchMt5Account = document.getElementById("btn-switch-mt5-account");
  if (btnSwitchMt5Account) {
    btnSwitchMt5Account.addEventListener("click", async () => {
      const elAcc = document.getElementById("cfg-mt5-account");
      const elPass = document.getElementById("cfg-mt5-password");
      const elSrv = document.getElementById("cfg-mt5-server");

      const accVal = elAcc ? elAcc.value.trim() : "";
      const passVal = elPass ? elPass.value.trim() : "";
      const srvVal = elSrv ? elSrv.value.trim() : "";

      if (!accVal || !passVal || !srvVal) {
        showToast("Mohon lengkapi Nomor Akun, Password, dan Server Broker MT5 Anda.", "warning");
        return;
      }

      const originalText = btnSwitchMt5Account.textContent;
      btnSwitchMt5Account.disabled = true;
      btnSwitchMt5Account.textContent = "Menghubungkan ke Broker MT5...";

      try {
        const res = await fetch("/api/mt5/switch-account", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account: parseInt(accVal),
            password: passVal,
            server: srvVal,
          }),
        });
        const data = await res.json();

        if (res.ok && data.success) {
          showToast(data.message || `Berhasil login ke Akun #${data.login} (${data.trade_mode})!`, "success");
          if (elPass) elPass.value = ""; // Bersihkan password dari form demi privasi
          await fetchStatus();
          await fetchPositions();
          await fetchHistoryPage();
          await loadSettingsIntoPageForm();
          await fetchChartData();
          await fetchSignals();
        } else {
          const errMsg = data.detail || data.error || "Gagal menghubungkan akun MT5.";
          showToast(`Gagal Login MT5: ${errMsg}`, "error");
        }
      } catch (err) {
        showToast(`Kesalahan jaringan: ${err}`, "error");
      } finally {
        btnSwitchMt5Account.disabled = false;
        btnSwitchMt5Account.textContent = originalText;
      }
    });
  }

  const btnSettingsBacktest = document.getElementById("btn-settings-open-backtest");
  if (btnSettingsBacktest) {
    btnSettingsBacktest.addEventListener("click", () => modalBacktest.classList.add("open"));
  }

  const btnSettingsLicense = document.getElementById("btn-settings-open-license");
  if (btnSettingsLicense) {
    btnSettingsLicense.addEventListener("click", async () => {
      modalLicense.classList.add("open");
      const res = await fetch("/api/license/verify", { method: "POST" });
      const data = await res.json();
      document.getElementById("lic-hw-id").value = data.hardware_id || "IDENTIFYING...";
      const badge = document.getElementById("lic-status-badge");
      badge.textContent = `Status: ${data.valid ? "Active (" + data.tier + ")" : "Invalid"}`;
      badge.style.color = data.valid ? "var(--accent-green)" : "var(--accent-red)";
    });
  }

  // =========================================================================
  // BOT CONTROLS (START / PAUSE)
  // =========================================================================
  async function toggleBot() {
    const endpoint = botIsRunning ? "/api/bot/stop" : "/api/bot/start";
    const res = await fetch(endpoint, { method: "POST" });
    const data = await res.json();
    showToast(data.message, "info");
    fetchStatus();
  }

  if (btnToggleBot) btnToggleBot.addEventListener("click", toggleBot);
  if (btnHeroBotAction) btnHeroBotAction.addEventListener("click", toggleBot);

  // =========================================================================
  // FUNDS CAROUSEL & WATCHLIST ROW INTERACTIONS (SHAKURO STYLE)
  // =========================================================================
  function setupSymbolCardInteractions() {
    document.querySelectorAll(".fund-card[data-symbol], .watchlist-row[data-symbol]").forEach((el) => {
      el.addEventListener("click", async () => {
        const sym = el.dataset.symbol;
        if (!sym) return;

        selectedSymbol = sym;
        localStorage.setItem("nexus_selected_symbol", selectedSymbol);

        // Highlight active card in carousel
        document.querySelectorAll(".fund-card").forEach((c) => {
          if (c.dataset.symbol === sym) c.classList.add("active");
          else c.classList.remove("active");
        });

        // Highlight active symbol button in chart bar
        document.querySelectorAll(".symbol-btn").forEach((b) => {
          if (b.dataset.symbol === sym) b.classList.add("active");
          else b.classList.remove("active");
        });

        if (chartActivePairName) chartActivePairName.textContent = sym;

        showToast(`Aset aktif disinkronkan ke: ${sym}`, "info");
        await quickSyncTrading({ symbols: [sym] });
        fetchLiveTick();
        fetchChartData();
        if (chart) chart.timeScale().fitContent();

        // If clicked on mobile, smoothly switch to chart execution view
        if (window.innerWidth <= 768) {
          switchView("chart");
        }
      });
    });

    const btnAddSymbol = document.getElementById("btn-add-symbol");
    if (btnAddSymbol) {
      btnAddSymbol.addEventListener("click", async () => {
        document.querySelectorAll(".symbol-btn").forEach((b) => {
          if (b.dataset.symbol === "ALL") b.classList.add("active");
          else b.classList.remove("active");
        });
        showToast("Bot disinkronkan: Memantau SEMUA 3 Pair!", "success");
        await quickSyncTrading({ symbols: ["EURUSD", "GBPUSD", "XAUUSD"] });
        fetchLiveTick();
        fetchChartData();
      });
    }

    const btnFundsViewAll = document.getElementById("btn-funds-view-all");
    if (btnFundsViewAll) {
      btnFundsViewAll.addEventListener("click", () => switchView("chart"));
    }

    // Category Tabs (Most Popular, Biggest Movers, AI Confluence)
    document.querySelectorAll(".cat-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".cat-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");

        const t = tab.dataset.tab;
        if (t === "radar") {
          const radarEl = document.querySelector(".radar-section");
          if (radarEl) radarEl.scrollIntoView({ behavior: "smooth" });
        }
      });
    });
  }

  // =========================================================================
  // MODALS (BACKTEST & LICENSE)
  // =========================================================================
  const btnOpenBacktest = document.getElementById("btn-open-backtest");
  if (btnOpenBacktest) {
    btnOpenBacktest.addEventListener("click", () => modalBacktest.classList.add("open"));
  }
  document.getElementById("btn-close-backtest").addEventListener("click", () => modalBacktest.classList.remove("open"));

  document.getElementById("btn-run-backtest-action").addEventListener("click", async () => {
    const symbol = document.getElementById("bt-symbol").value;
    const bars = parseInt(document.getElementById("bt-bars").value);
    const btn = document.getElementById("btn-run-backtest-action");

    btn.textContent = "⏳ Running Backtest Simulation...";
    btn.disabled = true;

    try {
      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, bars }),
      });
      const data = await res.json();
      btn.textContent = "Run Simulation";
      btn.disabled = false;

      if (data.success) {
        const m = data.metrics;
        document.getElementById("backtest-results-area").style.display = "block";
        document.getElementById("bt-winrate").textContent = `${m.win_rate}%`;
        document.getElementById("bt-profit").textContent = `$${m.net_profit.toFixed(2)}`;
        document.getElementById("bt-profit").style.color = m.net_profit >= 0 ? "var(--accent-green)" : "var(--accent-red)";
        document.getElementById("bt-pf").textContent = m.profit_factor;
        document.getElementById("bt-total-trades").textContent = m.total_trades;
        document.getElementById("bt-trades-winloss").textContent = `${m.win_count}W / ${m.loss_count}L`;
        document.getElementById("bt-drawdown").textContent = `$${m.max_drawdown_cash} (${m.max_drawdown_pct}%)`;
        document.getElementById("bt-expectancy").textContent = `$${m.expectancy} / trade`;
        showToast("Backtest simulation completed!", "success");
      } else {
        showToast("Backtest failed.", "error");
      }
    } catch (e) {
      btn.textContent = "Run Simulation";
      btn.disabled = false;
      showToast(`Backtest error: ${e}`, "error");
    }
  });

  const btnOpenLicense = document.getElementById("btn-open-license");
  if (btnOpenLicense) {
    btnOpenLicense.addEventListener("click", async () => {
      modalLicense.classList.add("open");
      const res = await fetch("/api/license/verify", { method: "POST" });
      const data = await res.json();
      document.getElementById("lic-hw-id").value = data.hardware_id || "IDENTIFYING...";
      document.getElementById("lic-key-input").value = "NEXUS-TRIAL-2026";
      const badge = document.getElementById("lic-status-badge");
      badge.textContent = `Status: ${data.valid ? "Active (" + data.tier + ")" : "Invalid"}`;
      badge.style.color = data.valid ? "var(--accent-green)" : "var(--accent-red)";
    });
  }

  document.getElementById("btn-close-license").addEventListener("click", () => modalLicense.classList.remove("open"));

  document.getElementById("btn-verify-license-action").addEventListener("click", async () => {
    showToast("License key verified and bound to this hardware.", "success");
    modalLicense.classList.remove("open");
  });

  // =========================================================================
  // BOOTSTRAP SYSTEM
  // =========================================================================
  function startChartWithRetry(retries = 15) {
    if (window.LightweightCharts && chartContainer) {
      initChart();
    } else if (retries > 0) {
      setTimeout(() => startChartWithRetry(retries - 1), 150);
    } else {
      console.error("Failed to load LightweightCharts library after retries.");
    }
  }

  updateCurrencyButton();
  setupSymbolCardInteractions();

  document.querySelectorAll(".symbol-btn").forEach((b) => {
    b.classList.remove("active");
    if (b.dataset.symbol === selectedSymbol) b.classList.add("active");
  });
  document.querySelectorAll(".tf-btn").forEach((b) => {
    b.classList.remove("active");
    if (b.dataset.tf === selectedTimeframe) b.classList.add("active");
  });

  startChartWithRetry();
  fetchStatus();
  fetchPositions();
  fetchSignals();
  fetchHistoryPage();
  loadSettingsIntoPageForm();
  fetchLiveUsdIdrRate(false);

  // Switch to initial view
  switchView(currentActiveView);

  // Periodic polling intervals
  setInterval(fetchStatus, 2500);
  setInterval(fetchPositions, 2000); // 2-second fast responsive polling for live positions
  setInterval(fetchLiveTick, 1500);  // 1.5-second live tick updater
  setInterval(fetchSignals, 5000);
  setInterval(() => fetchLiveUsdIdrRate(false), 600000); // 10-minute auto refresh live FX rate
  setInterval(() => {
    if (currentActiveView === "chart") {
      fetchChartData();
    }
  }, 4000);
});
