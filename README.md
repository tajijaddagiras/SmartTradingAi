# 🤖 NexusTrade AI — Desktop Automated Trading System

> Sistem bot trading mandiri (100% lokal, tanpa ketergantungan VPS) yang berpikir layaknya trader institusi menggunakan konfluensi 3 faktor, dilengkapi proteksi hardware lokal dan arsitektur siap SaaS.

---

## 🌟 Fitur Utama & Logika Sistem

1. **Mesin Penalaran AI (Triple-Confluence Engine):**
   - **Market Structure (Price Action):** Pemetaan otomatis pola *Higher High/Higher Low* (Uptrend) atau *Lower High/Lower Low* (Downtrend), serta level *Dynamic Support & Resistance*.
   - **Smart Money Concepts (SMC) & Volume:** Deteksi *Order Block (OB)* institusi dan anomali lonjakan volume perdagangan ($\ge 1.8\times$ baseline).
   - **Technical Filters:** Filter tren *EMA 50* (Harga > EMA untuk BUY) dan filter volatilitas *ATR* untuk membedakan koreksi wajar vs pembalikan tren riil.

2. **Manajemen Risiko & Proteksi Lokal (Safety First):**
   - **Server-Side Hard Stop Loss (Wajib):** Setiap pesanan yang dikirim ke server broker MT5 wajib menyertakan Hard Stop Loss. Jika laptop mati atau internet putus, modal tetap aman.
   - **Windows OS Anti-Sleep Daemon:** Menggunakan Win32 API `kernel32.SetThreadExecutionState` untuk mencegah komputer sleep/hibernate selama ada posisi aktif terbuka.
   - **Daily Drawdown Circuit Breaker:** Pembekuan (*Freeze Mode*) otomatis jika kerugian harian mencapai batas target (default: 3%).
   - **Spread Guard:** Mencegah eksekusi order saat spread melebar akibat *news volatility* atau sesi likuiditas rendah.

3. **Smart Trailing & Dynamic Exit ("Let Profits Run"):**
   - Tidak menggunakan *Take Profit* yang kaku. Stop Loss digeser secara dinamis (*trailing*) mengunci keuntungan seiring tren berlanjut.
   - **Dynamic Exit:** Menutup posisi lebih awal jika terdeteksi **Volume Exhaustion** (volume mengering saat harga menembus level baru) atau struktur pasar patah menembus batas wajar ATR.

4. **Kesiapan SaaS & Lisensi Terdistribusi:**
   - Modul lisensi dengan *Hardware Fingerprint* (SHA-256) unik per perangkat.
   - Eksekusi terdistribusi di laptop pengguna masing-masing, membebaskan pemilik platform dari biaya pemeliharaan server VPS berkapasitas besar.

---

## 📂 Struktur Direktori Proyek

```
nexus_trade_ai/
├── config/
│   ├── config.json          # Pengaturan parameter trading, risiko, dan lisensi
│   └── settings.py          # Validator skema otomatis berbasis Pydantic
├── core/
│   ├── engine.py            # Event loop & orkestrator sistem
│   ├── anti_sleep.py        # Windows Win32 OS Anti-Sleep Daemon
│   └── logger.py            # Sistem log rotasi & jurnal trading
├── mt5_bridge/
│   ├── connector.py         # Koneksi & watchdog MetaTrader 5
│   ├── market_data.py       # Ingest data OHLCV & konversi ke Pandas
│   └── executor.py          # Eksekusi order dengan Hard SL & Flat Before Close
├── risk/
│   ├── drawdown_limiter.py  # Daily Drawdown Circuit Breaker (-X% freeze)
│   ├── lot_calculator.py    # Perhitungan lot (Fixed & Dynamic Equity Risk %)
│   └── spread_guard.py      # Filter perlindungan spread liar / news spike
├── strategy/
│   ├── indicators.py        # Kalkulasi matematis: EMA, ATR, Volume SMA
│   ├── market_structure.py  # Deteksi HH/HL, LH/LL, S/R Dinamis
│   ├── smc_engine.py        # Deteksi Order Block & Volume Anomaly
│   ├── confluence.py        # Agregator sinyal (Triple-Factor Confluence)
│   └── smart_trailing.py    # Dynamic Trailing Stop & Volume Exhaustion Exit
├── backtest/
│   ├── backtest_runner.py   # Engine simulasi historis bar-by-bar
│   └── metrics.py           # Kalkulasi Win Rate, Profit Factor, Max Drawdown
├── licensing/
│   └── validator.py         # Hardware Fingerprint & License Key Verifier
├── tests/                   # Suite unit test terintegrasi (100% Passed)
├── logs/                    # Folder audit trail & trade journal
├── main.py                  # CLI entry point aplikasi
└── requirements.txt         # Dependensi Python
```

---

## 🚀 Panduan Menjalankan

### 1. Prasyarat
- Terminal **MetaTrader 5 (MT5)** sudah terinstal di komputer dan login ke akun trading (Demo atau Live).
- Fitur **Algo Trading** di MT5 sudah diaktifkan:
  - Buka MT5 $\rightarrow$ Menu **Tools** $\rightarrow$ **Options** $\rightarrow$ tab **Expert Advisors** $\rightarrow$ Centang **"Allow algorithmic trading"**.

### 2. Menjalankan Bot
Pilih mode yang ingin Anda gunakan:

* **Mode 1: Zen Desktop Web Dashboard (Rekomendasi UI):**
  Buka antarmuka visual modern di browser:
  ```powershell
  .\.venv\Scripts\python.exe main.py --ui
  ```
  Lalu buka **http://127.0.0.1:8899** di browser Anda.

* **Mode 2: Autonomous CLI Engine:**
  Menjalankan bot langsung di terminal:
  ```powershell
  .\.venv\Scripts\python.exe main.py
  ```

### 3. Perintah Tambahan

* **Simulasi Backtest Historis Langsung di Terminal:**
  ```powershell
  .\.venv\Scripts\python.exe main.py --backtest --symbol EURUSD --bars 400
  ```

* **Cek Status Koneksi & Saldo Akun MT5:**
  ```powershell
  .\.venv\Scripts\python.exe main.py --status
  ```

* **Emergency Flat Before Close (Tutup seluruh posisi instan):**
  ```powershell
  .\.venv\Scripts\python.exe main.py --flat-now
  ```

* **Menjalankan Seluruh Unit Test (100% Passed):**
  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover tests
  ```

---

## ⚙️ Kustomisasi Konfigurasi (`config/config.json`)

```json
{
  "system": {
    "mode": "demo",                  // "demo" atau "live"
    "loop_interval_seconds": 15
  },
  "trading": {
    "symbols": ["EURUSD", "GBPUSD", "XAUUSD"],
    "timeframe": "M15",
    "magic_number": 889900
  },
  "risk": {
    "use_fixed_lot": true,
    "fixed_lot_size": 0.01,          // Mode micro lot untuk uji coba
    "risk_per_trade_percent": 1.0,   // % risiko modal jika use_fixed_lot: false
    "max_daily_drawdown_percent": 3.0, // Circuit breaker batas rugi harian
    "max_open_positions": 3,
    "max_spread_points": 35
  },
  "confluence": {
    "ema_trend_period": 50,
    "atr_period": 14,
    "atr_multiplier_sl": 1.5,
    "volume_spike_multiplier": 1.8
  },
  "smart_trailing": {
    "enabled": true,
    "activation_atr_multiple": 1.0,
    "trail_step_atr_multiple": 0.5,
    "dynamic_exit_volume_exhaustion": true
  }
}
```
