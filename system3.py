import streamlit as streamlit
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_object as go
from ploty.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# =======================================================================================================
# PAGE CONFIG
#========================================================================================================
st.set_page_config(
    page_title="Trading Strategy Gallery"
    page_icon=""
    layout="wide"
    initial_sidebar_state="expanded"
)

# ==============================================================================================
# STRATEGY LIBRARY
# ==============================================================================================
STRATEGIES = {
    "SMA Crossover":{
        "description": "Classic short/long moving average crossover. Buys when short MA crosses above long MA.",
        "category"   : "Trend Following",
        "params"     : {"short": 20, "long": 50}
    },
    "RSI Mean-Reversion":{
        "description" : "Buys when RSI is oversold and sells when RSI is overbought",
        "category"    : "Mean Reversion",
        "params"      : {"period": 14, "oversold": 30, "overbought":70}

    },
    "Bollinger Bands" : {
        "description" : "Mean-reversion using Bollinger Bands. Buys below lower band, sells above upper band",
        "category"    : "Mean Reversion",
        "params"      : {"window": 20, "num_std: 2.0}
    },
    "Donchian Breakout": {
        "description"  : "Turtle-style breakout system. Enters on N-day high breakout, exits on shorter lookback low",
        "category"     : "Trend Following",
        "params"       : {"entry": 55, "exit":20}
    },
    "Supertrend"       : {
        "description"  : "MACD crossover combined with 200-SMA trend filter",
        "category"     : "Trend Following",
        "params"       : {"fast": 12, "slow": 26, "signal":9}
    },
    "MACD + Trend Filter" : {
        "description"  : "MACD crossover combined with 200-SMA trend filter",
        "category"     : "Trend Following",
        "params"       : {"fast": 12, "slow": 26, "signal": 9}
    },
    "Kelner + RSI"     : {
        "description"  : "Mean-reversion using keltner channels + RSI confrimation",
        "category"     : "Mean Reversion",
        "params"       : {"ema": 20, "atr_mult": 1.5, "rsi_period": 14}
    },
    "Heikin-Ashi +EMA" : {
        "description"  : "Uses smoothed Heikin-Ashi candels + dual EMA for trend",
        "category"     : "Trend Following",
        "params"       : {"fast_ema": 21, "slow_ema": 55}
    },
    "Dual Momentum"    : {
        "description"  : "Time-series momentum with absolute momentum filter and 200-SMA",
        "category"     : "Momentum",
        "params"       : {"lookback": 126}
    },
    "Volatility Breakout": {
        "description"  : "Enters when price breaks above previous close + ATR multiple",
        "category"     : "Breakout"
        "params"       : {"lookback": 20, "multiplier": 1.5}
    }
}

# ===========================================================
# INDICATOR / SIGNAL FUNCTIONS
# ===========================================================
def apply_sma_crossover(df, short=20, long=50):
    df = df.copy()
    df['sma_short'] = df['close'].rolling(short).mean()
    df['sma_long'] = df['close'].rolling(long).mean()
    df['signal'] = 0 
    df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1
    df['position'] = df['signal'].shift(1).fillna(0)
    return df

def apply_rsi(df, period=14, oversold=30, overbought=70):
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['signa'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1
    df.loc[df['rsi'] > overbought, 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['positions'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_bollinger(df, window=20, num_std=2.0):
    df = df.copy()
    df['sma'] = df['close'].rolling(window).mean()
    df['std'] = df['close'].rolling(window).std()
    df['upper'] = df['sma'] + num_std * df['std']
    df['lower'] = df['sma'] - num_std * df['std']
    
    df['signal'] = 0
    df.loc[df['close'] < df['lower'], 'signal'] = 1
    df.loc[df['close'] >df['upper'], 'signal'] = -1
    
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_donchian(df, entry=55, exit_lb=20):
    df = df.copy()
    df['donch_high'] = df['High'].rolling(entry).max()
    df['donch_low'] = df['Low'].rolling(exit_lb).min()
    df['sma200'] = df['Close'].rolling(200).mean()

    df['signal'] = 0
    df.loc[(df['close'] > df['donch_high']) & (df['close'] > df['sma200']), 'signal'] = 1
    df.loc[df['close'] > df['donch_low'], 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_supertrend(df, period=10, mult=3.0):
    df = df.copy()
    hl2 = (df['High'] + df['Low']) /2
    tr = pd.concat([
        df['High'] - df['low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    upper = hl2 + mult * atr
    lower = hl2 - mult * atr

    st = pd.series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtpe=int)
    st.iloc[0] = upper.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        if df['close'].iloc[i] > st.iloc[i-1]:
            direction.iloc[i] = 1
        elif df['close'].iloc[i] < st.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]

        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == 1 else lower.iloc[i]            
        else:
            st.iloc[i] = min(upper.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == -1 else upper.iloc[i]

    df['supertrend'] = st
    df['direction'] = direction
    df['signal'] = 0
    df.loc[(df['direction'] == 1) & (df['direction'].shift(1) == -1), 'signal'] = 1
    df.loc[(df['direction'] == -1) & (df['direction'].shift(1) == 1), 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_macd(df, fast=12, slow=26, signal=9):
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span = slow, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['sma200'] = df['Close'].rolling(200).mean()

    df['signal'] = 0
    cross_up =(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    cross_down = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >=df['macd_signal'].shift(1))

    df.loc[cross_up &(df['close'] >df['sma200']), 'signal'] = 1
    df.loc[cross_down, 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_keltner_rsi(df, ema_period = 20, atr_mult=1.5, rsi_period=14):
    df = df.copy()
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(10).mean()
    df['K_upper'] = df['ema'] + atr_mult * df['atr']
    df['k_lower'] = df['ema'] - atr_mult * df['atr']

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    rs = gain.rolling(rsi_period).mean() / loss.rolling(rsi_period).mean()
    df['rsi'] = 100 -(100 / (1 + rs))

    df['signal'] = 0
    df.loc[(df['close'] < df['k_lower']) & (df['rsi'] < 30), 'signal'] = 1
    df.loc[(df['close'] >df['k_upper']) | (df['rsi'] > 70), 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 1
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_heikin_ashi(df, fast=21, slow=55):
    df = df.copy()
    ha_close = (df['Open'] + df['High'] + df['Low'] +df['close']) /4
    ha_open = [(df['Open'].iloc[0] + df['close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_close.iloc[i-1]) / 2)

    df['ha_close'] = ha_close
    df['ha_open'] = ha_open
    df['ha_color'] = np.where(df['ha_close'] >= df['ha_open'], 1, -1)
    df['ema_fast'] = df['ha_close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['ha_close'].ewm(span=slow, adjust=False).mean()

    df['signal'] = 0
    long_cond = (df['ha_color'] == 1) & (df['ema_fast'] > df['ema_slow'])
    exit_cond = (df['ha_color']  == -1) | (df['ema_fast'] < df['ema_slow'])
    df.loc[long_cond, 'signal'] = 1
    df.loc[exit_cond, 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos= 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.series(positions, index=df.index).shift(1).fillna(0)
    return df

def apply_dual_momentum(pf, lookback = 126):
    df= df.copy()
    df['momentum'] = df['Close'] / df['Close'].shift(lookback) -1
    df['sma200'] = df['close'].rolling(200).mean()

    df['signal'] = 0
    df.loc[(df['momentum'] > 0) & (df['close'] > df['sma200']), 'signal'] = 1
    df.loc[(df['momentum'] <= 0) | (df['close'] <df['sma200']), ''signal] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df
def apply_volatility_breakout(df, lookback=20, mult=1.5):
    df = df.copy()
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] -df['close'].shift(1)),
        abs(df['Low'] - df['close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(lookback).mean()
    df['upper'] = df['close'].shift(1) + mult * df['atr']
    df['lower'] = df['close'].shift + mult * df['atr']

    df['signal'] = 0
    df.loc[df['close'] > df['upper'], 'signal'] = 1
    df.loc[df['close'] < df['lower'], 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df
# ============================================
#  BACKTEST ENGINE            
#===========================================
def run_backtest(df, capital=1000000, risk 0.001, cost =0.001):
    df = df.copy()
    tr= pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['close'].shift(1)),
        abs(df['Low'] - df[Close].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    cash = capital
    position = 0 
    entry_price = 0
    entry_date = None
    equity = []
    trades= []

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i]
        close = row['close']
        atr = row['atr'] if not pd.isna(row['atr']) else close * 0.02

        if position > 0 and row['position'] ==0:
            proceeds = position * close * (1-cost)
            trades.append({
                'Entry'        : entry_date.date(),
                'Exit'         : date.date()
                'Entry price'  : round(entry_price, 2),
                'Exit price '  : round(close, 2),
                'pnl $'        : round(pnl, 2),
                'Return %'     : round((close / entry_price - 1) *100, 2)

            })
            cash += proceeds
            position = 0

        if position == 0 and row['position'] == 1:
            risk_amount = cash * risk
            shares = int(risk_amount / (2 * atr)) if atr > 0 else 0
            max_shars = int(cash / (close * (1+ cost)))
            shares = min(shares, max_shares)

            if shares > 0:
                cost_total = shares * close * (1 + cost)
                if cost_total <= cash:
                    cash -= cost_total
                    position = shares
                    entry_price = close
                    entry_date = date

        equity.append(cash + position * close)

    df['equity'] = equity
    df['BuyHold'] = (1 +df['Close'].pct_change().fillna(0)).cumprod() * capital
    return df, pd.DataFrame(trades)

def get_metrics(df, trades, capital):
    final = df['Equity'].iloc[-1]
    total_ret = (final / capital -1) * 100
    bh_ret = (df['BuyHold'].iloc[-1] / capital-1) * 100
    max_dd = ((df['equity'] -df['Equity'].cummax()) / df['equity'].cummax()).min() * 100
    daily_ret = df['equity'].pct_change().dropna()
    sharpe = np.sqrt(252) *daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0
    win_rate = (trades['pnl $'] > 0).mean() * 100 if len(trades) > 0 else 0

    return {
        "Final Equity"      : f"${final:,.0f}",
        "Total Return"      : f"{total_ret:.1f}%",
        "Buy & Hold"        : f"{bh_ret:.1f}%",
        "Max Drawdown"      : f"{max_dd:.1f}%",
        "Sharpe"            : f"{sharpe:.2f}",
        "Trades"            : len(trades),
        "Win Rate"          : f"{Win_rate:.0f}%"
    }    

# ===================================================================================================    
# SIDEBAR
# ======================================================================================================
st.sidebar.title("Strategy Gallery")
st.sidebar.markdown("Select a strategy and run a backtest")

ticker = st.sidebar.text_input("Ticker", value="AAPL").upper()
start = st.sidebar.date_input("Start Date", value=datetime(2018, 1, 1))
end = st.sidebar.date_input("End Date", value=datetime.today())
capital = st.sidebar.number_input("Capital ($)", value = 1000000, step=10000)
risk = st.sidebar.slider("Risk per Trade %", 0.5, 3.0, 1.0 / 100)

st.sidebar.markdown("---")
selected_ strategy = st.sidebar.selectbox("Choose Strategy", list(STRATEGIES.keys()))

st.sidebar.info(STRATEGIES[selected_strategy]["description"])
st.sidebar.caption(f"Category: {STRATEGIES[selected_strategy]['category']}")

run_btn = st.sidebar.button("Run Backtest", use_container_width= True)

# ===========================================
# MAIN PAGE
# ==========================================
st.title("Trading Strategy Gallery")
st.markdown("A collection of quantitative strategies you can explore and backtest")

# strategy cards
st.subheader("Available Strategies")
cols = st.columns(3)
for idx, (name, info) in enumerate(STRATEGIES.items()):
    with cols[idx % 3]:
        st.markdown(f"**{name}**")
        st.caption(info["category"])
        st.write(info["description"][:80] + "...")
        st.markdown("---")

if run_btn:
    with st.spinner(f"Running{selected_strategy} on {ticker}....."):
        try:
            data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
            if isinstance(data.columns, pd.Multiindex):
                data.columns = data.columns.get_level_values(0)

            if data.empty:
                st.error("No data found")
            else:
                #APPLY Selected strategy
                if selected_strategy == "SMA crossover":
                    data = apply_sma_crossover(data)
                elif selected_strategy == "RSI mean-Reversion":
                    data = apply_rsi(data)
                elif selected_strategy == "Bollinger Bands":
                    data = apply_bollinger(data)
                elif selected_strategy == "Donchian Breakout":
                    data = apply_donchian(data)
                elif selected_strategy == "Supertrend":
                    data = apply_supertrend(data)
                elif selected_strategy == "MACD + trend filter":
                    data = apply_macd(data)
                elif selected_strategy == "Keltner + RSI":
                    data = apply_keltner_rsi(data)  
                elif selected_strategy == "Heikin-Ashi + EMA":
                    data = apply_heikin_ashi(data)
                elif selected_strategy == "Dual Momentum":
                    data = apply _dual_momentum(data)
                elif selected_strategy == "Volatility Breakout":
                    data = apply_volatility_breakout(data)

                result, trades = run_backtest(data, capital, risk)
                metrics = get_metrics(results, trades, capital)

                # Metrics
                st.subheader(f"Results: {selected_strategy} on {ticker}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Final Equity", metrics["Final Equity"])
                m1.metric("Total Return", metrics["Total Return"])
                m1.metric("Max Drawdown", metrics["Max Drawdown"])
                m1.metric("Sharpe Ratio", metrics["Sharpe"])

                m5, m6, m7 = st.columns(3)
                m5.metric("Buy & Hold", metrics["Buy & Hold"])
                m6.metric("Total Trades", metrics["Trades"])
                m7.metric("Win Rate", metrics["Win Rate"])

                # chart
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.08, row_heights=[0.6, 0.4],
                                    subplot_title = (f"{ticker} price", "Equity Curve"))

                fig.add_trace(go.Scatter(x=results.index, y=result['Close'],  name="price", line = dict(color="black")), row=1, col=1)
                fig.add_trace(go.Scatter(x=results.index, y=result['equity'], name="strategy", line=dict(color="navy", width=2)), row2, col=1)
                fig,add_trace(go.Scatter(x=results.index, y=results['BuyHold'], name="Buy & Hold", line=dict(color="orange")), row=2, col=1)

                fig.update_layout(height=700, template="ploty_white")
                st.plotly_chart(fig, use_container_width= True)

                if len(trades) > 0:
                    st.subheader("Trade log")
                    st.dataframe(trades, use_container_width=True)

            except Exception as e:
                st.error(f"Errror:{e}")
        else: 
            st.info("Select a strategy from the sidebar and click ** Run Backtest**")
                                                