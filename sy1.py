import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np 
import plotly.graph_object as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title= "NSE Kenya trading model",
    page_icon="📊",
    layout="wide"
)

# ===================================================================
# FULL Nairobi Stock Exchange STOCK DATABASE (searchable)
# ==================================================================
NSE_DATABASE = {
    "SCOM.NR"      : "Safaricom PLC",
    "EQTY.NR"      : "Equity Group Holding",
    "KCB.NR"       : "KCB Group",
    "COOP.NR"      : "Co-operative Bank of Kenya",
    "EABL.NR"      : "East African Bank of Kenya",
    "BAT.NR"       : "British American Tobacco Kenya",
    "NCBA.NR"      : "NCBA Group",
    "ABSA.NR"      : "Absa Bank Kenya"
    "SBIC.NR"      : "Stanbic Holdings",
    "IMH.NR"       : "I&M Holdings",
    "DTK.NR"       : "Diamond Trust Bank",
    "SCBK.NR"      : "Standard Chartered Bank Kenya",
    "BKG.NR"       : "BK Group",
    "JUB.NR"       : "Jubilee Holdings",
    "KQ.NR"        : "Kenya Power",
    "TOTL.NR"      : "National Media Group",
    "KEGN.NR"      : "Centum Investment",
    "CIC.NR"       : "CIC Insurance",
    "BRIT.NR"      : "Britam Holdings",
    "HFCK.NR"      : "HF Group",
    "LBTY.NR"      : "Liberty Kenya Holdings",
    "PORT.NR"      : "East African Portland Cement",
    "UNGA.NR"      : "Unga Group",
    "FIRE.NR"      : "Sammer Africa",
    "TCL.NR"       : "TPS Rastern Africa (Serena)",
    "WPP.NR"       : "WPP ScanGroup",
    "XPRS.NR"      : "Express Kenya"
}

# ===============================================================================
# STRATEGY FUNCTIONS
# ===============================================================================
def trend_volume_strategy(df, short=20, long=50):
    df = df.copy()
    df['sma_s'] = df['Close'].rolling(short).mean()
    df['sma_l'] = df['Close'].rolling(long).mean()
    df['vol_ma'] = df['Volume'].rolling(20).mean()

    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    df['signal'] = 0
    df.loc[(df['Close'] > df['sma_s']) & (df['close'] > df['sma_l']) &(df['Volume'] > df['vol_ma']), 'signal'] = 1
    df.loc[df['Close'] < df['sma_s'], 'signal'] = -1

    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index = df.index).shift(1).fillna(0)
    return df

def rsi_strategy(df, period=14, oversold=30, overbought=70):
    df = df.copy()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    rs = gainrolling(period).mean() / loss.rolling(period).mean()
    df['rsi'] = 100 - (100 / (1 + rs))

    tr = pd.concat([
        df['High'] - df['low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis =1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = -1
    
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos 1
        elif s == -1: pos =1
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def run_backtest(df, capital=500000, risk=0.012):
    df = df.copy()
    cash = capital
    position = 0
    entry_price = 0.0
    entry_date = None
    equity = []
    trades = []

    for i in range (len(df)):
        row = df.iloc[i]
        date = df.index[i]
        close = float(row['Close'])
        atr = float(rw['atr']) if nor pd.isna(row['atr']) else close * 0.03 

        if position > 0 and row['position'] == 0:
            proceeds = position * close * 0.992
            pnl = proceeds - (position * entry_price)
            trades.append({
                "Entry"        : entry_date.date(),
                "Exit"         : date.date(),
                "Entry Price"  : round(entry_price, 2),
                "Exit price"   : round(close, 2),
                "pnl (KES)"    : round(pnl, 0),
                "Return %"     : round((close / entry_price - 1) * 100, 2)
            })
            cash += proceeds
            position = 0

        if position == 0 and row['position'] == 1:
            shares = int((cash * risk) / (2 * atr)) if atr > 0 else 0
            shares = min(shares, int(cash / close))
            if shares > 0:
                cash -= shares * close * 1.008
                position = shares
                entry_price = close
                entry_date = date

        equity.append(cash + position * close)

    df['Equity'] = equity
    df['BuyHold'] = (1 + df['Close'].pct_change().fillna(0)).cumprod() * capital
    return df, pd.DataFrame(trades)

# ===============================================================================
# SIDEBAR -SEARCH SYSTEM
# ==============================================================================
st.sidebar.title("NSE Smart Search")

# search box
search_query = st.sidebar.text_input(
    "Search Stock (name or ticker)",
    placeholder = " e.g Safaricom,  Equity, SCOM, KCB..."
).strip().lower()

# Filter stocks based on search
if search_query:
    filtered = {
        k: v for k, v in NSE_DATABASE.items()
        if search_query in v.lower() or search_query in k.lower()
    }
else:
    filtered = NSE_DATABASE

    # Show filtered results
    if filtered:
        options = [f"{v} ({k})" for k, v in filtered.items()]
        selected_display = st.sidebar.selectionbox("Select from results", options)

        # Extract ticker
        ticker = selected_display.split("(")[-1].replace(")", "")
        stock_name = selected_display.split("(")[0]

    else: 
        st.sidebar.warning("No matching stocks found")
        ticker = "SCOM.NR"
        stock_name = "Safaricom PLC"

    st.sidebar.markdown(f"Selected:** '{ticker}'")

    # Manual ticker override
    st.sidebar.markdown ("----")
    manual_ticker = st.sidebar.text_input("Or type ticker manually", placeholder= "SCOM.NR")
    if manual_ticker:
        ticker = manual_ticker.upper().strip()
        stock_name = ticker

    # Other settings
    strategy = st.sidebar.selectbox("Strategy", ["Trend + volume", "RSI Mean Reversion"])
    start = st.sidebar.date_input("Start Date", datetime(2019, 1,1))
    end = st.sidebar.date_input("End Date", datetime.today())
    capital = st.sidebar.number_input("Capital (KES)", value = 50000, step=50000)
    risk = st.sidebar.slider("Risk Per Trade(%)", 0.5, 2.0, 1.2) / 100
    run_btn = st.sidebar.button("Run Backtest", use_container_width=True, type ="primary")

    # ===========================================================
    # MAIN PAGE
    # ===========================================================
    st.title("NSE Kenya Smart Trading System")
    st.caption("Search any Kenya stock and backtest strategies instantly")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.info(f"**Current Stock:** {stock_name} | **ticker:** '{ticker}'")
    with col_b:
        st.write(f"Strategy:** {strategy}")
    if run_btn:
        with st.spinner(f"Fetching {stock_name} data and running backtest..."):
            try:
                df = yf.download (ticker, start = start, end= end, auto_adjust=True, progess=False)

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                if df.empty or len(df) < 50:
                    st.error("Not enounh data found. Try another stock ( Safaricom, Equity, KCB work best)")
                else:
                    # Apply Strategy
                    if strategy == "Trend + Volume":
                        df = Trend_volume_strategy(df)
                    else:
                        df = rsi_strategy(df)
                    
                    results, trades = run_backtest(df, capital, risk)

                    # Metrics
                    final = results['Equity'].iloc[-1]
                    total_ret = (final / capital - 1) * 100
                    bh_ret = (result['BuyHold'].iloc[-1] / capital -1) * 100
                    max_dd = ((results['Equity'] - result['Equity'].cummax()) / results['Equity'].cummax()).min() * 100
                    daily_ret = result['Equity'].pct_change().dropna()
                    sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0
                    win_rate = (trades['pnl (KES)'] > 0).mean() * 100 if len(trades) > 0 else 0

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Final Equity", f"KES {final:,0f}")
                    m2.metric("Total Return", f"{total_ret:,.0f}%")
                    m3.metric("Max Drawdown", f{"max_dd:.1f"}%)
                    m4.metric("Sharpe Ratio", f"{sharpe:.2f}")

                    m5, m6, m7 = st.columns(3)
                    m5.metrics("Buy & Hold", f"{bh_ret:.1f}%")
                    m6.metrics("Total Trades", len(trades))
                    m7,metrics("Win Rate", f"{win_rate:.0f}%")

                    # Chart
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True
                        vertical_spacing =0.07,
                        row_heights= [0.58, 0.42],
                        subplo_titles = (f"{stock_name} price", "Equity Cutrve (KES)")
                    )

                    fig.add_trace(go.Scatter(
                        x=results.index, y=result['Close'], name="price",
                        line=dict(color="#0055ff", width=2.2)
                    ), row=1, col=1)

                    fig.add_trace(go.Scatter(
                        x=results.index, y=results['Equity'], name="Strategy",
                        line=dict(color="orange", width=1.5)
                    ), row=2, col=1)

                    fig.add_trace(go.Scatter(
                        x=results.index, y=results['BuyHold'], name="Buy & Hold",
                        line=dict(color="black", width=1.5)
                    ), row=2, col=1)

                    fig.update_layout(height=680, template="ploty_white")
                    st.ploty_chart(fig, use_container_width=True)

                    # Trades
                    if len(trades) > 0:
                        st.subheader("Trade log")
                        st.dataframe(trades, use_container_width= True)
                    else:
                        st.info("No trades were generated with current settings")

                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.mardown("""
                ### How to use this version
                1. **Type** in the search box (example: 'safar', 'equity', 'kcb', 'scom')
                2. The system will automatically filter matching kenyan stocks
                3. Select the stock you want
                4. Choose strategy and click **Run Backtest**

                you can also type ant ticker manually at the bottom of the sidebar.
                """)

                st.markdown("### Most Liquid Stocks")
                st.write("Safaricom . Equity Group . KCB .Co-operative Bank . EABL . BAT . NCBA")
                
        
