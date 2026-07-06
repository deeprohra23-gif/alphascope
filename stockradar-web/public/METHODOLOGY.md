# StockRadar India — Methodology

This document explains how every metric, score, and rating in the screener is calculated. All indicators are computed from daily OHLCV data (via Yahoo Finance) and fundamental data (scraped from screener.in). No AI predictions, no news sentiment — pure rule-based calculations.

---

## 📈 Trend & Regime Indicators

### Market Regime

A 4-factor composite classification that tells you the overall trend state of a stock. Each factor contributes ±1 to a total score:

| Factor | +1 if | -1 if |
|---|---|---|
| Price vs EMA 200 | Price above EMA 200 | Price below EMA 200 |
| Distance from 52W High | Better than -10% | Worse than -20% |
| ROC 6M | Positive | Negative |
| Trend Consistency (12M) | 8+ positive months | 4 or fewer positive months |

**Total score → Regime:**
- Score ≥ 3 → **Strong Bull**
- Score ≥ 1 → **Bull**
- Score ≥ -1 → **Bear**
- Score < -1 → **Strong Bear**

For indices, a 5th factor (Up Capture Ratio) is added, and thresholds shift to ±4/±2.

### Drawdown Status

Classifies how far a stock has fallen from its 52-week high:

- **At High** — within -2% of 52W High
- **Recovering** — between -10% and -2%, and within 60 days of the high
- **Correcting** — between -10% and -20%
- **Damaged** — below -20%

### EMA Cross

Compares the 50-day and 200-day Exponential Moving Averages:
- **Golden Cross** — EMA 50 > EMA 200 (long-term bullish structure)
- **Death Cross** — EMA 50 < EMA 200 (long-term bearish structure)

We also track `Days Since EMA Cross` to identify fresh crossovers.

### Supertrend

Standard Pine Script implementation with ATR(10) × 3 bands. The bands tighten as volatility shrinks and flip direction when price closes decisively through them. Returns **Bullish** or **Bearish**.

### MACD Signal

Standard 12/26/9 MACD. **Bullish** when MACD line is above signal line, **Bearish** otherwise.

### RSI 14

Standard 14-period Relative Strength Index using Wilder smoothing. Values:
- Above 70 → Overbought
- 50-70 → Bullish momentum
- 30-50 → Neutral
- Below 30 → Oversold

---

## ⚡ Momentum Indicators

### ROC (Rate of Change) 1M / 3M / 6M / 12M

Pure price change over the specified period:
```
ROC = (Current Price - Price N days ago) / Price N days ago × 100
```
Periods: 1M = 21 trading days, 3M = 63, 6M = 126, 12M = 252.

### Momentum Acceleration

Tells you whether momentum is speeding up or slowing down:
```
Momentum Acceleration = ROC 1M - (ROC 3M ÷ 3)
```
**Positive** = last month outpacing the recent average (accelerating).
**Negative** = last month slower than the average (decelerating).

### Momentum Quality

Return per unit of volatility — rewards "clean" momentum:
```
Momentum Quality = ROC 6M ÷ Annualized SD (1Y)
```
A stock up 40% with 50% volatility scores 0.8. One up 30% with 20% volatility scores 1.5 — cleaner trend.

### Trend Consistency (12M)

Count of months with positive returns in the last 12. Out of 12. Simple tally.

### RS vs Nifty (1M / 3M / 6M)

How much the stock outperformed (or underperformed) the Nifty index over the period:
```
RS = Stock ROC - Nifty ROC
```
Positive = outperforming, negative = underperforming.

---

## 🛡️ Risk & Volatility

### SD 1Y %

Annualized standard deviation of daily returns over 1 year:
```
SD 1Y = Daily Return StdDev × √252 × 100
```

### ATR % (14D)

Average True Range over 14 days, expressed as % of current price. Measures typical daily price range.

### Beta 1Y (Daily)

OLS regression slope of stock's daily returns vs Nifty's daily returns over 1 year. Standard CAPM beta.
- Beta > 1 → amplifies market moves
- Beta < 1 → dampens market moves
- Beta ≈ 0 → uncorrelated with market

### Beta 5Y (Monthly)

Same calculation on monthly returns over 5 years. Long-term market sensitivity.

### 1Y Max Drawdown %

Largest peak-to-trough decline over the past year, expressed as negative %.

### Vol Trend / Vol Ratio

Ratio of 20-day SD to 60-day SD (both annualized):
```
Vol Ratio = SD(20D) ÷ SD(60D)
```
- Ratio > 1.15 → **Rising** volatility
- Ratio < 0.85 → **Falling** volatility
- Between → **Stable**

### Up / Down Capture Ratio

On days Nifty went **up**, what % of Nifty's gain did the stock capture?
On days Nifty went **down**, what % of Nifty's loss did the stock take?

- **Up Capture** > 100 → outperforms on rallies
- **Down Capture** < 100 → falls less on declines
- Ideal stock: high Up Capture, low Down Capture

### Capture Ratio

```
Capture Ratio = Up Capture ÷ Down Capture
```
Above 1 is ideal.

---

## 🏆 Composite Scores

All three sub-scores are on a 0-100 scale. Missing data is handled gracefully — weights are renormalized to only include components with data.

### Technical Score

Weighted blend:
| Component | Weight |
|---|---|
| Market Regime | 20% |
| Drawdown Status | 15% |
| Trend Consistency | 15% |
| EMA Cross | 10% |
| MACD | 10% |
| Supertrend | 10% |
| Vol Trend | 10% |
| RSI | 10% |

RSI uses a custom curve that peaks at 65-70 (bullish momentum zone), not a linear scale — overbought RSI >70 is penalized just like oversold <30.

### Momentum Score

Weighted blend — each ROC component is **percentile-ranked within the universe**, so scores are comparative:
| Component | Weight |
|---|---|
| ROC 3M | 20% |
| ROC 6M | 20% |
| RS vs Nifty 3M | 20% |
| ROC 1M | 15% |
| Momentum Quality | 15% |
| Momentum Acceleration | 10% |

### Fundamental Score

| Component | Weight | Higher is better? |
|---|---|---|
| ROCE | 15% | Yes |
| ROE | 15% | Yes |
| Net Profit Margin | 10% | Yes |
| Sales Growth 3Y | 10% | Yes |
| Profit Growth 3Y | 10% | Yes |
| Promoter Holding | 10% | Yes |
| Debt/Equity | 10% | No (inverse) |
| Pledge % | 10% | No (inverse) |
| PE vs Sector PE | 10% | See below |

**PE vs Sector PE band scoring:**
- PE < 0.7 × Sector PE → score 100
- PE < 1.0 × Sector PE → score 75
- PE < 1.3 × Sector PE → score 50
- PE ≥ 1.3 × Sector PE → score 25

### Composite Score & Universe Rank

```
Composite Score = (Technical + Momentum + Fundamental) ÷ 3
Universe Rank = ranking by Composite Score within the current filtered universe
```

---

## 🎯 Insights (Buy / Sell / Hold Ratings)

Rule-based ratings, not AI predictions. Cascading priority — strongest rating wins when multiple match.

### Technical Insight

**Strong Buy** — ALL of:
- Market Regime = Strong Bull
- Supertrend = Bullish
- MACD = Bullish
- Price > EMA 50 > EMA 200
- RSI between 50 and 70

**Buy** — ALL of:
- Market Regime in [Bull, Strong Bull]
- Supertrend = Bullish
- MACD = Bullish OR Price > EMA 50
- RSI > 45

**Strong Sell** — ALL of:
- Market Regime = Strong Bear
- Supertrend = Bearish
- MACD = Bearish
- Drawdown Status = Damaged

**Sell** — ALL of:
- Market Regime in [Bear, Strong Bear]
- Supertrend = Bearish
- MACD = Bearish OR Price < EMA 50

**Hold** — everything else, or if critical data is missing.

### Fundamental Insight

**Strong Buy** — ALL of:
- ROCE > 20%
- ROE > 18%
- D/E < 0.5
- Profit Growth 3Y > 15%
- EPS Growth 3Y > 15%
- PE < Sector PE
- Promoter Holding > 50%

**Buy** — ALL of:
- ROCE > 15%
- ROE > 12%
- D/E < 1
- Profit Growth 3Y > 10%
- EPS Growth 3Y > 10%
- Sales Growth 3Y > 8%

**Strong Sell** — ALL of:
- ROCE < 5%
- Profit Growth 3Y < 0%
- EPS Growth 3Y < 0%
- D/E > 2
- Pledge > 30%

**Sell** — ANY of:
- ROCE < 8%
- Profit Growth 3Y < 0%
- EPS Growth 3Y < -10%
- D/E > 2
- PE > 3 × Sector PE

**Hold** — everything else, or if core fundamental data is missing.

---

## 💰 Trade Setup (Stock Card)

ATR-based **reference levels** for someone considering entry at the current price. These are illustrative, not investment advice.

### Entry

Current market price. (The screener assumes you're looking at fresh entry, not managing an existing position.)

### Stop Loss

```
ATR Stop = Entry - (1.5 × ATR)
```

If the stock is in Bull or Strong Bull regime AND EMA 200 is below current price:
```
Final Stop = max(ATR Stop, EMA 200 × 0.98)
```
This is because EMA 200 often acts as meaningful support in uptrends. The 2% buffer below EMA 200 gives a bit of breathing room.

### Targets

```
Risk per share = Entry - Stop
Target 1 = Entry + (2 × Risk)    # 1:2 risk-reward
Target 2 = Entry + (3 × Risk)    # 1:3 risk-reward
```

### Key Reference Levels

Shown for context: 52W High, 52W Low, EMA 50, EMA 200. These are **not** the entry/stop/target — they're just there so you can see what important price levels are nearby.

---

## 🔔 What Changed Today

Compares today's data to the most recent previous snapshot. Requires at least 2 days of historical snapshots to function.

Signals detected:
- **Fresh Golden/Death Cross** — EMA Cross flipped today
- **Regime Upgraded/Downgraded** — Market Regime improved or worsened
- **Entered Strong Bull/Strong Bear** — regime reached an extreme
- **Newly At High / Newly Damaged** — Drawdown Status transitioned
- **Supertrend Flipped** — Supertrend reversed direction today

---

## 📊 Screen Performance Tracking

For each pre-built screen, we look at snapshots from 1M / 3M / 6M ago, re-run the screen on that past data, then compute how those picks performed (price change) up to today.

Shown as:
- **Avg Return** — simple average return of all picks
- **Winners / Losers** — count of positive vs negative returns
- **Win Rate** — % of picks that ended positive

Requires accumulated snapshots to populate. Starts showing 1M data after ~30 days of automated runs.

---

## ⚠️ Important Notes

**What this is:** A screening and monitoring tool. It cuts 880+ stocks down to a manageable shortlist based on consistent rules.

**What this isn't:** Investment advice, price predictions, or guaranteed signals. All ratings are rule-based — a stock can show "Strong Buy" and still fall, or "Strong Sell" and rally. Context and judgment always matter.

**Data sources:**
- Technical data (prices, volumes) — Yahoo Finance, daily refresh
- Fundamental data — screener.in, updated monthly
- Index membership — NSE, updated quarterly

**Data limitations:**
- Fundamentals are TTM or latest available, not real-time
- Yahoo Finance data can have gaps for thinly-traded stocks
- Some recently listed stocks may lack sufficient history for certain indicators (3Y CAGR, 5Y Beta, etc.)

**This tool is for educational and research purposes only. Please consult a SEBI-registered financial advisor before making investment decisions.**
