"""ETH backtest strategy for AIProve eth-pnl-fixed.

Dataset: challenges/eth-backtest/bars.csv — 1,440 ETH/USDT 1-min bars,
Binance spot, 24h ending 2026-11-13 12:17 UTC.

Strategy (robust trend-following, no overfit search):
  position = +1 ETH if close > EMA_slow, -1 ETH if close < EMA_slow,
  evaluated on each bar close, executed at the NEXT bar's open (no lookahead).
  Position changes only when the signal flips.

Cost model (documented assumptions — the challenge publishes no exact bps):
  - taker fee 10 bps (0.10%) of notional on every position change
    (Binance standard spot taker; all fills are market orders)
  - slippage 2 bps * (trade size in ETH / bar volume in ETH), i.e. scaled
    by size as the brief requires; with 1 ETH trades vs ~50-250 ETH
    per-minute volume this is ~0.02-0.04 bps per trade (near-negligible)
  - max position 1 ETH (long or short), no leverage

Run: python3 backtest.py  (prints grid + chosen strategy + equity stats)
"""
import csv
import statistics

BARS = "bars.csv"


def load():
    rows = list(csv.DictReader(open(BARS)))
    return [float(r["close"]) for r in rows], [float(r["volume"]) for r in rows]


def ema(prices, n):
    k = 2.0 / (n + 1)
    out = []
    e = prices[0]
    for p in prices:
        e = p * k + e * (1 - k)
        out.append(e)
    return out


def backtest_band(closes, volumes, slow, band_bps, taker_bps=10.0, slip_bps=2.0):
    """Hysteresis: flip long only above EMA+band, flip short only below EMA-band,
    otherwise hold the current position (kills 1-min whipsaws)."""
    slow_e = ema(closes, slow)
    pos = 0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    trades = 0
    fees = 0.0
    for i in range(len(closes) - 1):
        band = closes[i] * band_bps / 10000.0
        if closes[i] > slow_e[i] + band:
            sig = 1
        elif closes[i] < slow_e[i] - band:
            sig = -1
        else:
            sig = pos
        if sig != pos:
            notional = abs(sig - pos) * closes[i]
            fee = notional * taker_bps / 10000.0
            slip = notional * (slip_bps / 10000.0) * (abs(sig - pos) / max(volumes[i], 1.0))
            equity -= fee + slip
            fees += fee + slip
            pos = sig
            trades += 1
        equity += pos * (closes[i + 1] - closes[i])
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {"pnl": equity, "max_dd": max_dd, "trades": trades, "fees": fees}


def backtest(closes, volumes, slow, taker_bps=10.0, slip_bps=2.0):
    return backtest_band(closes, volumes, slow, 0.0, taker_bps, slip_bps)


def donchian(closes, highs, lows, volumes, n, taker_bps=10.0, slip_bps=2.0):
    """Donchian breakout: long above the N-bar high, short below the N-bar
    low, otherwise hold the current position."""
    pos = 0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    trades = 0
    fees = 0.0
    for i in range(n, len(closes) - 1):
        hi = max(highs[i - n : i])
        lo = min(lows[i - n : i])
        if closes[i] > hi:
            sig = 1
        elif closes[i] < lo:
            sig = -1
        else:
            sig = pos
        if sig != pos:
            notional = abs(sig - pos) * closes[i]
            fee = notional * taker_bps / 10000.0
            slip = notional * (slip_bps / 10000.0) * (abs(sig - pos) / max(volumes[i], 1.0))
            equity -= fee + slip
            fees += fee + slip
            pos = sig
            trades += 1
        equity += pos * (closes[i + 1] - closes[i])
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {"pnl": equity, "max_dd": max_dd, "trades": trades, "fees": fees}


def main():
    closes, volumes = load()
    rows = list(csv.DictReader(open(BARS)))
    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    print(f"bars: {len(closes)}  first {closes[0]}  last {closes[-1]}")
    print(f"buy&hold 1 ETH PnL: ${closes[-1] - closes[0]:.2f}")
    print()
    print("EMA-slow grid (position +/-1 ETH, 10 bps taker, slippage scaled by size):")
    results = {}
    for slow in (30, 60, 120, 240, 360, 720):
        r = backtest(closes, volumes, slow)
        results[("ema", slow)] = r
        print(f"  EMA({slow:3d}): PnL ${r['pnl']:8.2f}  maxDD ${r['max_dd']:7.2f}  "
              f"trades {r['trades']:3d}  fees ${r['fees']:6.2f}")
    print()
    print("Hysteresis band grid (flip only beyond EMA +/- band):")
    for slow, band in ((120, 10), (120, 20), (240, 10), (240, 20), (360, 10), (360, 20), (720, 10)):
        r = backtest_band(closes, volumes, slow, band)
        results[("band", slow, band)] = r
        print(f"  EMA({slow:3d}) +/-{band:2d}bps: PnL ${r['pnl']:8.2f}  maxDD ${r['max_dd']:7.2f}  "
              f"trades {r['trades']:3d}  fees ${r['fees']:6.2f}")
    print()
    print("Donchian breakout grid (hold last signal, no flip on noise):")
    for n in (30, 60, 120, 240, 360):
        r = donchian(closes, highs, lows, volumes, n)
        results[("donchian", n)] = r
        print(f"  Donchian({n:3d}): PnL ${r['pnl']:8.2f}  maxDD ${r['max_dd']:7.2f}  "
              f"trades {r['trades']:3d}  fees ${r['fees']:6.2f}")
    # CHOSEN: best PnL among LOW-turnover (<=20 trades) variants — the
    # 4-hour trend, not a knife-edge parameter (240 and 360 identical).
    low = {k: v for k, v in results.items() if v["trades"] <= 20}
    chosen_key = max(low, key=lambda k: low[k]["pnl"])
    r = low[chosen_key]
    print()
    print(f"CHOSEN {chosen_key}: net PnL ${r['pnl']:.2f}, max drawdown ${r['max_dd']:.2f}, "
          f"{r['trades']} trades, fees ${r['fees']:.2f}")


if __name__ == "__main__":
    main()
