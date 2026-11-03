import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

#==================================================================================
# PAGE CONFIG
# =================================================================================
st.set_page_config(
    page_title="python Trading System",
    page_icon="",
    layout = "wide",
    initial_sidebar_state ="expand"
)

#===================================================================================
# STRATEGY FUNCTIONS
#==================================================================================
def calculate_sma_crossover(df, short=20, long=50):
    df = df.copy()
    df['sma_short'] = df['close'].rolling(short).mean()
    df['sma_long'] = df['close'].rolling(long).mean()

    df['signal'] = 0
    df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1
    df['position'] = df['signal'].shift(1).fillna(0)
    return df

def calculate_rsi_strategy(df, period=14, oversold=30, overbought=70):
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss 
    df['rsi'] = 100 - (100 / (1+rs))

    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1
    df.loc[df['rsi'] > overbought, 'signal'] = -1

    position = 0
    positions = []
    for sig in df['signal']:
        if sig == 1:
            position = 1
        elif sig == -1:
            position = 0
        positions.append(position)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def calculate_donchian(df, entry=55, exit_lookback=20):
    df = df.copy()
    df['donch_high'] = df['High'].rolling(entry).max()
    df['donch_low'] = df['Low'].rolling(exit_lookback).min()
    df['sma_200'] = df['close'].rolling(200).mean()

    df['signal'] = 0
    df.loc[(df['close'] > df['donch_high']) & (df['close'] > df['sma_200']), 'signal'] =1
    df.loc[df['close'] <['donch_low'], 'signal'] = -1

    position = 0
    position = []
    for sig in df['signal']:
        if sig == 1:
            position = 1
        elif sig == -1:
            position = 0
        positions.append(position)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def calculate_supertrend(df, period=10, multiplier=3.0):
    df = df.copy()

    hl2 = (df['High'] +df['Low']) / 2
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] -df['Close'].shift(1)),
        abs(df['Low'] -df['Close'].shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    supertrend.iloc[0] = upper.iloc[0]
    direction.iloc[0] = 1

    for  i in range(1, len(df)):
        if df['Close'].iloc[i] > supertrend.iloc[i-1]:
            direction.iloc[i] =1
        elif df['Close'].iloc[i] < supertrend.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == 1 else lower.iloc[i]
        else:
            supertrend.iloc[i] = min(upper.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == -1 else upper.iloc[i]

    df['supertrend'] = supertrend
    df['direction'] = direction

    df['signal'] = 0
    df.loc[(df['direction'] == 1) & (df['direction'].shift(1) == -1), 'signal'] = 1
    df.loc[(df['direction'] == -1) & (df['direction'].shift(1) == 1), 'signal']  = -1

    position = 0
    positions = []
    for sig in df['signal']:
        if sig == 1:
            position = 1
        elif sig == -1:
            position = 0
        position.append(position)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

#========================================================================================================
# BACKTEST ENGINE
# =======================================================================================================
def run_backtest(df, capital = 5000000, risk_per_trade=0.01, cost=0.001):
    df = df.copy()

    # ATR for sizing
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    cash = capital
    position = 0
    entry_price = 0
    entry_date = None
    equity = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i]
        clse = row['close']
        atr = row['atr'] if not pd.isna(row['atr'])

        # Exit
        if position > 0 and row['position'] == 0:
            proceeds = position * close * (1 - cost)
            pnl = proceeds - (position * entry_price)
            pnl_pct = (close / entry_price - 1) * 100
            trades.append({
                'Entry Date'    : entry_date.date(),
                'Exit Date'     : date.date(),
                'Entry Price'   : round(entry_price, 2),
                'Exit price'    : round(close, 2),
                'Shares '       : position,
                'pnl $'         : round(pnl, 2),
                'Return %'      : round(pnl_pct, 2)

            })  
            cash += proceeds
            position = 0

        # Entry
        if position == 0 and row['position'] == 1:
            risk_amount = cash * risk_per_trade
            stop_distance = 2 * atr
            shares = int(risk_amount / stop_distance)
            max_shares = int(cash / (close * (1 + cost)))
            shares = min(shares, max_shares)

            if shares > 0:
                cost_total = shares * close *(1 + cost)
                if cost_total <= cash:
                    cash -= cost_total
                    position =  shares
                    entry_price = close
                    entry_date = date

        equity.append(cash + position * close)

    df['equity'] = equity
    df['BuyHold'] = (1 + df['close'].pct_change().fillna(0)).cumprod() * capital

    return df, pd.DataFrame(trades)
    def calculate_metrics(df, trades, capital):
        final = df['Equity'].iloc[-1]
        total_return = (final / capital -1) * 100
        bh_return = (df['BuyHold'].iloc[-1] / capital -1) * 100

        peak = df['equity'].cummax()
        max_dd = ((df['Equity'] - peak) / peak).min() * 100

        daily_ret = df['Equity'].pct_change().dropna()
        sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0

        win_rate = (trades['pnl $'] > 0).mean() * 100 if len(trades) > 0 else 0

        return{
            'Final Equity'         : f"${final:,.2f}",
            'Total Return'         : f"{total_return:.2f}%",
            'Buy & Hold'           : f"{bh_return:.2f}%",
            'Max Drawdown'         : f"{max_dd:.2f}%",
            'Sharpe Ration'        : f"{sharpe:.2f}",
            'Total Trades'         : len(trades),
            'Win Rate'             : f"{win_rate:.1f}%"
        }
        # ================================================================
        # SIDEBAR -CONTROLS
        #==================================================================
        st.sidebar.title("Trading System Contols")

        ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper()
        start_date = st.sidebar.date_input("Ticker Symbol", value=datetime(2015, 1, 1))
        end_date = st.sidebar.date_input("End Date", value=datetime.today())

        strategy_name = st.sidebar.selectbox(
            "Select Strategy",
            ["SMA Crossover", "RSI Mean-Reversion", "Donchian Breakout", "Supertrend"]
        )

        capital = st.sidebar.number_input("Initial Capital ($)", value=250000, step=10000)
        risk = st.sidebar.slider("Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1) / 100

        st.sidebar.markdown("---")
        st.sidebar.subheader("Strategy Parameters")

        if strategy_name == "SMA Crossover":
            short_window = st.sidebar.slider("Shoert SMA", 5, 50, 20)
            long_window = st.sidebar.slider("Lomg SMA", 20, 200, 50)
        elif strategy_name == "RSI Mean-Reversion":
            rsi_period = st.sidebar.slider("RSI Period", 7, 21, 14)
            oversold = st.sidebar.slider("Oversold Level", 15, 40, 30)
            overbought = st.sidebar.slider("Overbought Level",60, 85, 70)
        elif strategy_name == "Donchian Breakout":
            entry_lookback = st.sidebar.slider("Entry lookback", 20, 100, 55)
            exit_lookback = st.sidebar.slider("Exit lookback", 10, 50, 20)
        elif strategy_name == "supertrend":
            st_period = st.sidebar.slider("ATR Period", 7, 20, 10)
            st_mult = st.sidebar.slider("ATR Multiplier", 1.5, 5.0, 3.0, 0.1)

        run_button = st.sidebar.button("Run Backtest", use_container_width=True)

#=================================================================================================
# MAIN AREA
#=================================================================================================
st.title("Python Trading System")
st.markdown("Professional Backtesting Interface")

if run_button:
    with st.spinner(f"Downloading {ticker} data and running backtest"):
        try:
            # Download data
            df = yf.download(ticker, start=start_date, end = end_date, auto_adjust=True, progress=False)

            if isinstance(df.columns, pd.Multiindex):
                df.columns = df.columns.get_level_values(0)

            if df.empty:
                st.error("No data found for this ticker and date range")
            else:
                # Apply strategy
                if strategy_name == "SMA Crossover":
                    df = calculate_sma_crossover(df, short_window, long_window)
                elif strategy_name == "RSI Mean-Reversion":
                    df = calculate_rsi_strategy(df, rsi_period, oversold, overbought)
                elif strategy_name == "Donchian Breakout":
                    df = calculate_donchian(df, entry_lookback, exit_lookback)
                elif strategy_name == "Supertrend":
                    df = calculate_supertrend(df, st_period, st_mult)

                # Run backtest
                result_df, trades = run_backtest(df, capital, risk)
                metrics = calculate_metrics(result_df, trades, capital)

                # ==================== METRICS ===================
                st.subheader("performance summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Final Equity", metrics['Final Equity'])
                col2.metric("Total Return", metrics['Total Return'])
                col3.metric("Max Drawdown", metrics['Max Drawdown'])
                col4.metric("Sharpe Ratio", metrics['Sharpe Ratio'])

                col5, col6, col7 = st.columns(3)
                col5.metric("Buy & Hold Return", metrics['Buy & Hold'])
                col6.metric("Total Trades", metrics['Total trades'])
                col7.metric("Win Rate", metrics['Win Rate'])

                # ============== CHARTS =================\
                st.subheader("Equity Curve & Price")

                fig = make_subplots(
                    rows= 2, col=1,
                    shared_taxes=True,
                    vertical_spacing = 0.08,
                    row_height=[0.6, 0.4],
                    subplot_titles =(f"{ticker} price", "Equity Curve")

                )

                fig.add_trace(
                    go.Scatter(x=result_df.index, y=results_df['close'], name='price', line=dict(color='black')),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=results_df.index, y=results_df['Equity'], name='Strategy', line=dict(color='navy', width =2)),
                    row=2, col=1

                )
                fig.add_trace(
                    go.scatter(x=results_df.index, y= results_df['BuyHold'], name='Buy & Hold', line=dict(color='orange', width = 1.5)),
                    row=2, col=1
                )
                gig.update_layout(height=700, template='plotly_white', showlegend=True)
                st.ploty_charts(fig, use_container_width=True)

                #============================= TRADES TABLE =======================
                if len(trades)>0:
                    st.subheader("Trade log")
                    st.dataframe(trades, use_container_witdh=True)
                   else:
                    st.info("No trades generated with current parameters")

            except Exception as e:
                st.error(f"Error:{e}")

        else:
            st.info("Asjust parameters in the sidebar and click ** Run Backtest** to start")
            st.markdown("""
            ### Available Strategies:
            # - **SMA Crossover** - classic moving average crossover
            # -**RSI Mean-Reversion** - Buy oversold, sell overbought
            # -**Donchian Breakout** - Turtle-style channel breakout
            # -**Supertrend** - ATR-based trend following
            ### Features:
            # - Risk-based position sizing
            # -Transaction cost included
            # - Interactive charts
            # - Full trade log
            """)        




                            

