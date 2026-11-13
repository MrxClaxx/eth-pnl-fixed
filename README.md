# eth-pnl-fixed — backtest report

Bounty: `eth-pnl-fixed` — Highest backtest PnL on the fixed ETH dataset
(2,000,000 PROVE, closes 20 Nov 2026 20:49 WIB, AutoGrade, metric: net PnL
after costs, ties break on lower max drawdown).

## Dataset
`bars.csv` — 1,440 ETH/USDT 1-minute bars, Binance spot, 24h ending
2026-11-13 12:17 UTC. Open $2,028.68 → close $1,960.59 (-3.36%).
Shape: choppy range ~$1,998–$2,029 until ~13:00 UTC, then a sharp drop to
~$1,928 by ~17:00 UTC, then a choppy recovery to $1,960.59.

## Strategy (submitted code: `strategy.py`)
Donchian 240-minute breakout, position in {-1, 0, +1} ETH, max 1 ETH,
no leverage. Long on a break above the 240-bar high, short on a break
below the 240-bar low, otherwise hold. Signals on bar close, executed at
next bar's open (no lookahead).

Trades on this sample (exactly 2):
- ~12:18 UTC short at $2,006.03 (broke the 240-min low) — rides the drop
- ~21:47 UTC flip long at $1,948.26 (broke the 240-min high) — rides the recovery

## Cost model (assumptions — the challenge publishes no exact bps)
- Taker fee 10 bps of notional per position change (Binance standard spot
  taker; all fills are market orders)
- Slippage 2 bps × (trade size / bar volume), scaled by size per the brief
  (~0.02–0.04 bps at 1 ETH — near-negligible)

## Results (1 ETH, 10 bps taker)
- **Net PnL: +$64.19**
- **Max drawdown: $48.10**
- Trades: 2, fees: $5.91
- Buy & hold 1 ETH: -$68.09

Fee sensitivity (Donchian 240): 0 bps → +$70.10; 2 bps → +$68.92;
5 bps → +$67.15; 10 bps → +$64.19; 20 bps → +$58.29. Robust to the
fee assumption.

Families tested (all 1 ETH, 10 bps taker): EMA-cross was negative at every
lookback (EMA 30: -$885.99, EMA 120: -$328.98, EMA 360: -$154.71 — 1-min
noise whipsaws + fees eat the trend). EMA + 20 bps hysteresis band best
-$36.95. Donchian 60: +$3.81, 120: +$0.71, 240: +$64.19, 360: +$64.19
(identical to 240 — same 2 trades, so the result is the 4-hour trend,
not a knife-edge parameter).

## Submission status — BLOCKED
`eth-pnl-fixed` has submitKind **repo**: it requires a public GitHub repo
at one commit + build transcript. No GitHub account exists for this agent
and creating one was explicitly out of scope. Strategy code is ready in
this folder (`strategy.py`, `backtest.py`, `bars.csv`, `positions.csv`) —
if a GitHub repo becomes available, push this folder and submit
`repoUrl` + commit + transcript via the API.
