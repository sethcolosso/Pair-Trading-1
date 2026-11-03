import flet as ft
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ===========================================
# STRATEGY FUNCTIONS
# ===========================================
def sma_crossover(df, short=20, long=50):
    df = df.copy()
    df['sma_s'] = df['Close'].rolling(short).mean()
    df['sma_l'] = df['Close'].rolling(long).mean()
    df['signal'] = 0
    df.loc[df['sma_s'] > df['sma_l'], 'signal'] = 1
    df['position'] = df['signal'].shift(1).fillna(0)
    return df
def rsi_strategy(df, period=14, oversold = 30, overbought=70):
    df = df.copy()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    rs = gain.rolling(period).mean()/ loss.rolling(period).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    df['signal'] = 0
    df.loc[df['rsi'] < oversold, 'signal'] = 1
    df.loc[df['rsi'] > overbought, 'signal'] = -1  
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def donchian(df, entry=55, exit_lb=20):
    df = df.copy()
    df['high_n'] = df['High'].rolling(entry).max()
    df['low_n'] = df['low'].rolling(exit_lb).min()
    df['sma200'] =  df['Close'].rolling(200).mean()
    df['signal'] = 0
    df.loc[(df['close'] > df['high_n']) &(df['close'] > df['sma200']), 'signal'] = 1
    df.loc[df['close'] < df['low_n'], 'signal'] = -1
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df
def supertrend(df, period=10, mult=3.0):
    df = df.copy()
    hl2 = (df['High'] + df['Low']) / 2
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df[close'].shift(1))
    ], axis=1.max(axis=1))       
    atr =tr.rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 = mult * atr
    st = pd.Series(index=df.index, dtype=int)
    st.iloc[0] = 1
    direction.iloc[0] = 1
    for i in range(1, len(df)):
        if df['close'].iloc[i] > st.iloc[i-1]:
            direction.iloc[i] = 1
        elif df['Close'].iloc[i] < st.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower.iloc[i],st.iloc[i-1]) if direction.iloc[i-1] == 1 else lower.iloc[i]
        else:
            st.iloc[i] = min(upper.iloc), st.iloc[i-1], if direction.iloc[i-1] == -1 else upper.iloc[i]
    df['direction'] = direction
    df['signal'] = 0
    df.loc[(df['direction'] == 1) & (df['direction'].shift(1) == -1), 'signal'] =1
    df.loc[(df['direction'] == -1) & (df['direction'].shift(1) == 1), 'signal'] = -1
    pos = 0 
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(position, index = df.index).shift(1), fillna(0)
    return df

def dual_momentum(df, lookback = 126):
    df = df.copy()
    df['mom'] = df['Close'] / df['Close'].shift(lookback) - 1
    df['sma200'] df['close'].rolling(200).mean()
    df['sidnal'] = 0
    df.loc[(df['mom'] > 0) & (df['close'] >df['sma200']), 'signal'] = 1
    df.iloc[(df['mom'] <=) | (df['close'] ,df['sma200']), 'signal'] = -1
    pos = 0
    positions  = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos =0
        positions.append(pos)
    df['position'] = pd.Series(positions, index =df.index).shift(1).fillna(0)
    return df

STRATEGIES = {
    "SMA Crossover"      : sma_crossover,
    "RSI Mean-Reversion" : rsi_strategy,
    "Donchian Breakout"  : donchian,
    "Supertrend"         : supertrend,
    "Dual Momentum"      : dual_momentum
}

# =====================================================================
# BACKTEST ENGINE
# =====================================================================
def run_backtest(df, capital=1000000, risk=0.01):
    df = df.copy()
    tr = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift(1)),
        abs(df['Low'] - df['Close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr']= tr.rolling(14).mean()

    cash = capital
    position = 0
    equity = []

    for i in range(len(d)):
        row = df.iloc[i]
        close = row['close']
        atr = row['atr'] if not pd.insta(row['atr']) else close * 0.02

        if position == 0 and row['position'] == 1:
            shares = int((cash * risk) / (2 * atr)) if atr > 0 else 0
            shares = min(shares, int(cash / close))
            if shares > 0:
                cash -= shares * close * 1.001
                position = shares
        equity.append(cash + position * close)
    df['Equity'] = equity
    df['BuyHold'] = (1 + df['close'].pct_change().fillna(0)).cumprod() * capital
    return df

# ===========================================================================
# FLET APP
# ===========================================================================\
def main(page: ft.page):
    page.tittle = "Trading Strategy Gallery"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window_width = 1200
    page.window_height = 800
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --------------------- Controls -------------------
    strategy_dd = ft.Dropdown(
        label = "strategy",
        options = [ft.dropdown.Option(k) for k in STRATEGIES.keys()],
        value = "SMA Crossover"
        width = 280,

    )
    ticker_tf = ft.TextField(label = "Ticker", valuw="MSTF", width=150)
    start_tf = ft.TextField(label = "Start Year", value="2018", width= 120)
    capital_trades = ft.TextField(label = "Capital", value="1000000", width = 150)

    # Metrics cards
    metric_final = ft.Text("-", size=20, weight=ft.FontWeight.BOLD)
    metric_return = ft.Text("-", size=20, weight=ft.FontWeight.BOLD)
    metric_sharpe = ft.Text("-", size=20, weight=ft.FontWeight.BOLD)
    metric_dd = ft.Text("-", size=20, weight=ft.FontWeight.BOLD)
    metric_trades = ft.Text("-", size=20, weight=ft.FontWeight.BOLD)

    def create_metric_card(title, value_control):
        return ft.Container(
            content =ft.Column([
                ft.Text(title, size=13, color=ft.Colors.Grey_400),
                value_control,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding = 15,
            border_radius = 12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            width = 160,
            height = 90,
            alignment=ft.alignment.center,
        )

    metrics_row = ft.Row([
        create_metric_card("Final Equity", metric_final),
        create_metric_card("Total Return", metric_return),
        create_metric_card("Max Drawdown", metric_dd),
        create_metric_card("Sharpe Ratio", metric_sharpe),
        create_metric_card("Trades", metric_trades),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)

    result_text = ft.Text("", size=14, selectable=True)
    progress = ft.ProgressRing(visible=False, width=30, height=30)

    # -------------------- Run Logic -----------------
    def run_clicked(e):
        progress.visible = True
        results_text.value = "Running backtest...."
        page.update()

        try:
            ticker = ticker_tf.value.upper().strip()
            start = f"{start_tf.value.strip()} -01-01"
            capital = float(capital_tf.value)
            strategy_name = strategy_dd.value

            df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty:
                results_text.value = "No data found for this ticker"
                progress.visible = False
                page.update()
                return
            strategy_func = STRATEGIES[sttrategy_name]
            df = strategy_func(df)
            result = run_backtest(df, capital)

            final = results['Equity'].iloc[-1]
            total_ret = (final / capital -1) * 100
            max_dd = ((result['Equity'] - result['Equity'].cummax()) / result['Equity'].cummax()).min() * 100
            daily_ret = results['Equity'].pct_change().dropna()
            sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std if daily_ret.std() > 0 else 0
            trades = int(((results['position'] == 1) & (results['position'].shift(1) == 0)).sum())

            metric_final.value = f"${final:,.0f}"
            metric_return.value = f"{total_ret:.1f}%"
            metric_dd.value = f"{max_dd:.1f}%"
            metric_trades.value = str(trades)

            results_text.value = f"Strategy: {strategy_name} | Ticker: {ticker} | Finished successfully"

        except Exeption as ex:
            result_text.value = f"Error: {ex}"

        progress.visible = False
        page.update()

    run_btn = ft.ElevateButton(
        "Run Backtest",
        icon =ft.icons.PLAY_ARROW,
        on_click = run_clicked,
        style =  ft.ButtonStyle(padding=20),
        height = 50,
    )    

    # ----------------------- Layout ----------------------
    page.add(
        ft.Text("Trading Strategy Gallery", size=28, weight = ft.fontWeight.BOLD),
        ft.text("Pure python Fronted powerd by Flet", size=14, color=ft.Colors.Grey_400),
        ft.Divider(heigt=30),
        ft.Row([
            strategy_dd,
            ticker_tf,
            start_tf,
            capital_tf,
            run_btn,
            progress,
        ], alignment = ft.MainAxisAlignment.CENTER, spacing=15),
        ft.Container(height=25)
        metrics_row,
        ft.Container(height=25),
        metric_row,
        ft.Container(height=20),
        result_text,
    )
    # ===============================================================
    # START
    # ===============================================================
    if __name__ == "__main__":
        ft.app(target=main)