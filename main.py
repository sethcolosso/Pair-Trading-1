# ============================================================
# INSTITUTIONAL PAIRS TRADING ENGINE (AUTO PAIR SELECTION)
# Rolling Hedge Ratio + Regime Filter + Sharpe Train/Test
# ============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import yfinance as yf
import itertools

# ============================================================
# USER INPUT SECTION
# ============================================================

initial_capital = float(input("Enter total portfolio capital: "))
max_portfolio_loss_pct = float(input("Max portfolio loss % before stop (e.g. 20): ")) / 100
max_drawdown_pct = float(input("Max drawdown % allowed (e.g. 15): ")) / 100

transaction_cost_rate = 0.000005   # 50 bps
vol_target_annual = 0.15

# ============================================================
# 1. DOWNLOAD DATA UNIVERSE
# ============================================================

universe = [
    'GLD','GDX','SLV','XLE','XOP',
    'SPY','QQQ','IWM',
    'KO','PEP','XOM','CVX'
]

data = yf.download(
    universe,
    start='2023-01-01',
    end='2026-10-07',
    auto_adjust=True,
    progress=False
)

prices = data['Close'].dropna()

# ============================================================
# 2. FIND MOST COINTEGRATED PAIR
# ============================================================

best_pvalue = 1
best_pair = None

for pair in itertools.combinations(prices.columns, 2):
    s1 = prices[pair[0]]
    s2 = prices[pair[1]]

    score, pvalue, _ = coint(s1, s2)

    if pvalue < best_pvalue:
        best_pvalue = pvalue
        best_pair = pair

print("\nMost Cointegrated Pair:", best_pair)
print("Best p-value:", best_pvalue)

asset1, asset2 = best_pair

# ============================================================
# 3. TRAIN / TEST SPLIT
# ============================================================

train_days = int(len(prices) * 0.7)   # 70% training

trainset = np.arange(0, train_days)
testset = np.arange(train_days, len(prices))

# ============================================================
# 4. ROLLING HEDGE RATIO
# ============================================================

window = 60
rolling_beta = []

for i in range(len(prices)):
    if i < window:
        rolling_beta.append(np.nan)
    else:
        X = prices[asset2].iloc[i-window:i]
        X = sm.add_constant(X)
        Y = prices[asset1].iloc[i-window:i]
        model = sm.OLS(Y, X).fit()
        rolling_beta.append(model.params[asset2])

rolling_beta = pd.Series(rolling_beta, index=prices.index)

# ============================================================
# 5. BUILD SPREAD
# ============================================================

spread = prices[asset1] - rolling_beta * prices[asset2]

rolling_mean = spread.rolling(window).mean()
rolling_std = spread.rolling(window).std()

zscore = (spread - rolling_mean) / rolling_std

# ============================================================
# 6. COINTEGRATION FILTER (TRAINING PERIOD ONLY)
# ============================================================

score, pvalue, _ = coint(
    prices[asset1].iloc[trainset],
    prices[asset2].iloc[trainset]
)

is_stationary = pvalue < 0.05

print("\nTrain Period Cointegration p-value:", pvalue)
print("Stationary Regime (Train)?", is_stationary)

# ==========
# 7. SIGNALS
# ========================

positions = pd.DataFrame(index=prices.index, columns=[asset1, asset2])
positions[:] = 0

if is_stationary:

    positions.loc[zscore >= 4, asset1] = -1
    positions.loc[zscore >= 2, asset2] = rolling_beta

    positions.loc[zscore <= -4, asset1] = 1
    positions.loc[zscore <= -2, asset2] = -rolling_beta

    exit_condition = (zscore < 1) & (zscore > -1)
    positions.loc[exit_condition] = 0

positions = positions.ffill().fillna(0)

# ============================================================
# 8. RETURNS + VOL TARGETING
# ============================================================

returns = prices[[asset1, asset2]].pct_change().fillna(0)

raw_pnl = (positions.shift(1) * returns).sum(axis=1)

rolling_vol = raw_pnl.rolling(60).std() * np.sqrt(252)
vol_scaler = vol_target_annual / rolling_vol
vol_scaler = vol_scaler.clip(upper=3)

scaled_pnl = raw_pnl * vol_scaler

# ============================================================
# 9. TRANSACTION COSTS
# ============================================================

position_change = positions.diff().abs().sum(axis=1)
transaction_cost = position_change * transaction_cost_rate

net_pnl = scaled_pnl - transaction_cost

print("Total Transaction Cost:", transaction_cost.sum())

# ============================================================
# 10. EQUITY CURVE + RISK CONTROLS
# ============================================================

equity = initial_capital * (1 + net_pnl).cumprod()

drawdown = equity / equity.cummax() - 1
max_dd = drawdown.min()

print("Max Drawdown:", max_dd)

stopouts = (drawdown < -max_drawdown_pct).sum()
print("Drawdown Stopouts:", stopouts)

if max_dd < -max_portfolio_loss_pct:
    print("Portfolio stopped due to max loss breach")

# ============================================================
# 11. SHARPE RATIOS (TRAIN & TEST)
# ============================================================

def sharpe_ratio(series):
    if series.std() == 0:
        return 0
    return np.sqrt(252) * series.mean() / series.std()

sharpe_train = sharpe_ratio(net_pnl.iloc[trainset])
sharpe_test = sharpe_ratio(net_pnl.iloc[testset])

print("\nSharpe Ratio (Train):", sharpe_train)
print("Sharpe Ratio (Test):", sharpe_test)

# ============================================================
# 12. TRADE STATISTICS
# ============================================================

trade_entries = (positions.diff() != 0).any(axis=1)
trade_count = trade_entries.sum()

trade_returns = net_pnl[trade_entries]
wins = (trade_returns > 0).sum()
losses = (trade_returns <= 0).sum()

print("\nTotal Trades:", trade_count)
print("Winning Trades:", wins)
print("Losing Trades:", losses)

# ============================================================
# 13. PLOTS
# ============================================================

upper = rolling_mean + 3 * rolling_std
lower = rolling_mean - 3 * rolling_std

plt.figure(figsize=(12,6))
plt.plot(spread, label='Spread')
plt.plot(rolling_mean, linestyle='--', label='Rolling Mean')
plt.plot(upper, linestyle='--')
plt.plot(lower, linestyle='--')
plt.title(f"Spread: {asset1} vs {asset2}")
plt.legend()
plt.show()

plt.figure(figsize=(12,6))
plt.plot(equity)
plt.title("Equity Curve (After Costs & Vol Targeting)")
plt.ylabel("Portfolio Value")
plt.show()