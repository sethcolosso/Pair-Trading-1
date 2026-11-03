import customtkinter as ctk
from tkinter import messagebox
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backend_tkagg import FigureCanvasTkAgg
import threading
import warnings
warnings.filterwarnings("ignore")

# ====================================================
# APPEARANCE 
# ====================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ====================================================
# STRATEGY FUNCTIONS
# ====================================================
def sma_crossover(df, short=20, long=50):
    df = df.copy()
    df['sma_s'] = df['Close'].rolling(short).mean()
    df['sma_l'] = df['Close'].rolling(long).mean()
    df['signal'] = 0
    df.loc[df['sma_s'] > df['sma_l'], 'signal'] = 1
    df['position'] = df['signal'].shift(1).fillna(0)
    return df

def rsi_strategy(df, period=14, ob=30, os_=70):
    df = df.copy()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    rs = gain.rolling(period).mean() / loss.rolling(period).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    df['signal'] = 0
    df.loc[df['rsi'] < ob, 'signal'] = 1
    df.loc[df['rsi'] > os_, 'signal'] = -1
    pos = 0
    positions = []
    for s in df ['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def donchian(df, entry=55, exit_lb=20):
    df = df.copy()
    df['high_n'] = df['High'].rolling(entry).max()
    df['low_n']  = df['Low'].rolling(exit_lb).min()
    df['sma200'] = df['Close'].rolling(200).mean()
    df['signal'] = 0
    df.loc[(df['Close'] > df['high_n']) & (df['close'] > df['sma200']), ' signal'] =1 
    df.loc[df['Close'] < df['low_n'], 'signal'] = -1
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos =1
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def donchian(df, entry=55, exit_lb=20):
    df = df.copy()
    df['high_n'] = df['High'].rolling(entry).max()
    df['low_n'] = df['Low'].rolling(exit_lb).min()
    df['sma200'] = df['Close'].rolling(200).mean()
    df['signal'] = 0
    df.loc[(df['Close'] > df['high_n']) & (df['Close'] >df['sma200']), 'signal'] = 1
    df.loc[df['Close'] < df['low_n'], 'signal'] = -1
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
    tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df ['Close'].shift(1)), abs(df['low'] - df['Close'].shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    st.iloc[0] = upper.iloc[0]
    direction.iloc[0] = 1
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > st.iloc[i-1]:
            direction.iloc[i] = 1
        elif df['Close'].iloc[i] < st.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]:
        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == 1 else lower.iloc[i]
        else:
            st.iloc[i] min(upper.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == -1 else upper.iloc[i]
    df['direction'] = direction
    df['signal'] = 0
    df.loc[(df['direction'] == 1) & (df['direction']).shift(1) == -1, 'signal'] = 1
    df.loc[(df['direction'] == -1) & (df['direction']).shift(1) == 1, 'signal'] = -1
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

def dual_momentum(df, lookback=126):
    df = df.copy()
    df['mom'] = df['close'] / df['Close'].shift(lookback) - 1
    df['sma200'] = df['Close'].rolling(200).mean()
    df['signal'] = 0
    df.loc[(df['mom'] > 0) & (df['close'] > df['sma200']), 'signal'] = 1
    df.loc[(df['mom'] <= 0) | (df['close'] < df['sma200']), 'signal'] = -1
    pos = 0
    positions = []
    for s in df['signal']:
        if s == 1: pos = 1
        elif s == -1: pos = 0
        positions.append(pos)
    df['position'] = pd.Series(positions, index=df.index).shift(1).fillna(0)
    return df

STRATEGIES = {
    "SMA Crossover": sma_crossover,
    "RSI Mean-Reversion": rsi_strategy,
    "Donchian Breakout": donchian,
    "Supertrend": supertrend,
    "Dual Momentum": dual_momentum
}                                 

# ================================================================
# BACKTEST====================
#=========================================================
def run_backtest(df, capital=1000000, risk=0.01):
    df = df.copy()
    tr = pd.concat([df['High'] -df['low'], abs(df['High']- df['close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    cash = capital
    position = 0
    entry_price = 0
    equity = []

    for i in range(len(df)):
        row = df.iloc[i]
        close = row['close']
        atr = row['atr'] if not pd.isna(row['atr']) else close * 0.02

        if position > 0 and row['position'] == 0:
            cash += position * close * 0.999
            position = 0
        if position == 0 and row['position'] == 1:
            shares = int((cash * risk) / (2 * atr)) if atr > 0 else 0
            shares = min(shares, int(cash/ close))
            if shares > 0:
                cash -= shares * close * 1.001
                position = shares
                entry_price = close
        equity.append(cash + position * close)

    df['Equity'] = equity
    df['BuyHold'] = (1 + df['close'].pct_change().fillna(0)).cumprod() * capital
    return df

# ==============================================================================================
# #  MAIN APP
# # ===========================================================================================
class TradingGalleryApp(ctk.CTK):
    def __init__(self):
        super().__init__()

        self.title("Trading Strategy Gallery - pure Python UI")
        self.geometry("1280 * 800")
        self.minsize(1100, 700)

        # Main layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ====================LEFT SIDEBAR=========================
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column =0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        ctk.CtkLabel(self.sidebar, text="Strategy Gallery", font=ctk.CTkFont(size=14)).pack(pady=(15,5), padx=20, anchor="w")

        self.strategy_var = ctk.StringVar(value="SMA crossover")
        self.strategy_menu = ctk.CTKOptionMenu(
            self.sidebar,
            values = list(STRATEGIES.keys()),
            variable = self.strategies_var,
            width = 240
        )
        self.strategy_menu.pck(pady=5, padx=20)

        ctk.CTkLabel(self.sidebar, text="Ticker", font=ctk.CTkFont(size=14)).pack(pady=(20,5), padx=20, anchor="w")
        self.ticker_entry = ctk.CTkEntry(self.sidebar, width = 240, placeholder_text="TSLA")
        self.ticker_entry.insert(pady=5, padx=20)

        ctk.CTkLabel(self.sidebar, text="start Year" font=ctk.CTkEntry(size =14)).pack(pady = (20, 5), padx=20, anchor="w")
        self.start_entry = ctkEntry(self.sidebar, width=240)
        self.start_entry.insert(0, "2018")
        self.start_entry.pack(pady=5, padx=20)

        ctk.CTkLabel(self.sidebar, text="Capital ($)", font=ctk.CTkfont(size=14)).pack(pady=(15, 5), padx=20, anchor"w")
        self.capital_entry = ctk.CTkEntry(self.sidebar, width=240)
        self.capital_entry.insert(0, "1000000")
        self.capital_entry.pack(pady=5, padx=20)

        self.run_btn = ctk.CTkButton(
            self.sidebar,
            text="Run Backtest",
            command=self.start_backtest,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.run_btn.pack(pady=30, padx=20)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Ready", text_color="gray")
        self.status_label.pack(pady=10)

        # ============== RIGHT MAIN AREA ===========================
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Metrics frame
        self.metrics_frame = ctk.CTkFrame(self.main_frame)
        self.metrics_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.metric_label = {}
            metrics_name = ["Final Equity", "Total Return", "Max Drawdown", "Sharpe", "Trades"]
            for i, name in enumerate(metric_names):
                frame = ctk.CTkFrame(self.metrics_frame)
                frame.grid(row=0, column=i, padx=8, pady=10, sticky="ew")
                self.metrics_frame.grid_columnconfigure(i, weigh=1)
                ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(size =18)).pack(pady=(8,0))
                lbl = ctk.CTklabel(frame, text="-", font=ctk.CTkFont(size=18, weight="bold"))
                lbl.pack(pady=(0, 8))
                self.metric_labels[name] = lbl

        # Chart area
        self.chart_frame = ctk.CTkFrame(self.main_frame)
        self.chart_frame.grid(row=2, column=0, sticky="nsew")

        self.fig = None
        self.canvas = None

        # Welcome message
        self.welcome = ctk.CTkLabel(
            self.chart_frame,
            text="Select a strategy and click Run Backtest",font=ctk.CTkfont(size=16)

        )   
        self.welcome.pack(expand = True)

    def start_backtest(self):
        try:
            ticker = self.ticker_entry.get().upper().strip()
            start_year = self.start_entry.get().strip()
            capital = float(self.capital_entry.get())
            strategy_name = self.strategy_var.get()

            start_date = f"{start_year} -01-01"

            df = yf.download(ticker, start=start_date, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.Multiindex):
                df.columns = df.columns.get_level_values(0) 

            if df.empty:
                self.after(0, lambda: messagebox.showerror("Error", "No data found"))
                return

            strategy_func =  STRATEGIES[strategy_name]
            df = strategy_func(df)
            results = run_backtest(df, capital)

            # Metrics
            final = results['Equity'].iloc[-1]
            total_ret = (final / capital - 1) * 100
            max_dd = ((result['Equity'] - results['Equity'].cummax()) / results['Equity'].cummax()).min() * 100
            daily_ret = result['Equity'].pct_change().dropna()
            sharpe = np.sqrt(252) * daily_ret.mean()/ daily_ret.std() ifdaily_ret.std() > 0 else 0
            trades = ((result['position'] == 1) & (result['position'].shift(1) == 0)).sum()

            metric = {
                "Final Equity"     : f"${final:,.0f}",
                "Total Return"     : f"{total_ret:.1f}%",
                "Max Drawdown"     : f"{max_dd:.2f}",
                "Trades"           : str(trades),
                "Sharpe"           : f"{sharpe:.2f}"
            }        

            self.after(0, lambda: self.update_ui(result, metrics, strategy_name, ticker))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal", text="Run Backtest"))
            self.after(0, lambda: self.status_label.configure(text="Ready"))

    def update_ui(self, results, metric, strategy_name, ticker):
        # Update metrics
        for name, value in metrics.items():
            self.metric_labels[name].configure(text= value)

            # Clear previous chart\
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
            if self.welcome:
                self.welcome.destroy()
                self.welcome = None

            # New chart
            self.fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [1.5, 1]})

            ax1.plot(results.index, result['Close'], color= 'black', linewidth = 1)
            ax1.set_title(f"{ticker} - {strategy_name}", fontsize=13)
            ax1.grid(True, alpha=0.3)

            ax2.plot(result.index, result['Equity'], color='navy', linewidth=1.5, label='Strategy')
            ax2.plot(result.index, result['BuyHold'], color='orange', alpha=0.7, label='Buy & Hold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.set_ylabel("Equity ($)")

            plt.tight_layout()

            self.canvas = figurecanvasTkAgg(self.fig, master = self.chart_frame)
            self.canvas.draw()
            self.cancas.get_tk_widget().pack(fill="both", expand=True)

# =======================================================
# RUN APP
#======================================================
if __name__ == "__main__":
    app = tradingGalleryApp()
    app.mainloop()


                


        
