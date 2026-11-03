import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.fliterwarnings("ingore")

class IchimokuCloudStrategy:
    def __init__(
        self,
        ticker="MSFT",
        start="2016-01-01",
        end="2026-02-07",
        capital=4000000,
        risk_per_trade= 0.01,
        atr_period =14
        atr_multiplier=2.5,
        transaction_cost=0.001,
        tenkan_period=9,
        kijun_period =26,
        senkou_b_period=52,
        displacement = 26
    ):
      
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_capital = capital
        self.risk_per_trade  = risk_per_trade
        self.atr_multiplier = atr_ period
        self.atr_period = atr_period
        self.transaction_cost = transaction_cost

        # Ichimoku Setting (Classic)
        self.tenkan_period = taenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement

        self.data= None
        self.trades = []

def fetch_data(self):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Downloading {self.ticker}...")
    df = yf,download(self.ticker, start=self.start, end=self.end, auto_adjust=True, progress=False)

    if isinstance(df.colums, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    self.data = df
    print(f"loaded {leen(df)} bars | {df.index[0].data()} - {df.index[-1].date()}")
    return self
def add_ichimoku(self):
    df = self.data.copy()

    # Tenkan-sen (Conversion Line)
    tenkan_high = df['high'].rolling(self.tenkan_period).max()
    tenkan_low = df['low'].rolling(self.tenkan_period).min()
    df['tenkan'] = (tenkan_high + kijun_low) /2

    # Kijun-sen (Base Line)
    kijun_high = df['high'].rolling(self.kijun_period).max()
    kijun_low = df['low'].rolling(self.kijun_period).min()
    df['kijun'] = (kijun_high + kijun_low) /2

    # Senkou Span A (Leading Span A)
    df['senkou_a'] = ((df['tenkan'] + df['kijun']) /2).shift(self.displacement)
    
    # Senkou Span B (Leading Span B)
    senkou_b_high = df['high'].rolling(self.senkou_b_period).max()
    senkou_b_low = df['low'].rolling(self.senkou_b_period).min()
    df['senkou_b'] = ((senkou_b_high + senkou_b_low) /2).shift(self.displacement)

    # Chikou Span (Lagging Span)
    df['chikou'] = df['close'].shift(-self.displacement)

    # Cloud top & bottom
    df['cloud_top'] = df[['senkou_a', 'senkou_b']].max(axis=1)
    df['cloud_bottom'] = df [['senkou_a', 'senkou_b']].min(axis=1)

    # ATR for position sizing
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))
    low_close = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(self.atr_period).mean()

    self.data = df
    return self

def generate_signals(self):
    df = self.data.copy()

    # Conditions
    price_above_cloud = df['close'] > df['cloud_top']
    tk_cross_up = (df['tenkan'] > df['kijun']) & (df['tenkan'].shift(1) <= df['kijun'].shift(1))
    tk_cross_down = (df['tenkan'] < df ['kijun']) & (df['tenkan'].shift(1) >= df['kijun'].shift(1))

    # Chikou Confirmation (Chikou is shifted, so we look at current close vs past close)
    chikou_above = df['close'] > df['close'].shift(self.displacement)

    # Strong bullish signal
    long_entry = price_above_cloud & tk_cross_up & chikou_above

    # Exit Signals
    price_below_cloud = df['close'] < df['cloud_bottom']
    long_exit = price_below_cloud | tk_cross_down

    df['signal'] = 0
    df.loc[long_entry, 'signal'] = 1
    df.loc[long_exit,  'signal'] = -1

    self.data = df
    return self

def run_backtest(self):
    df = self.data.copy()

    cash = self.initial_capital
    position = 0
    entry_price = 0.0
    entry_date = None

    equity_list = []
    trade_log = []

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i]
        close = row['close']
        atr = row['atr']

        if pd.isna(atr) or atr == 0 or pd.isna(row['cloud_top']):
            equity_list.append(cash + position * close)
            continue

        # ======================== EXIT ==================
        if position  > 0:
            if row ['signal'] == -1:
                exit_price = close
                proceeds = position * exit_price *(1 - self.transaction_cost)
                pnl = proceeds - (position * entry_price)
                pnl_pct = (exit_price / entry_price - 1) *  100

                trade_log.append(
                    {
                        'entry_date'           : entry_date,
                        'exit_date'            : date,
                        'entry_price'          : round(entry_price, 2),
                        'exit_price'           : round(exit_price, 2),
                        'shares'               : position,
                        'pnl'                  : round(pnl, 2)
                        'return_pct'           : round(pnl_pct, 2)
                        'reason'               : 'cloud / TK Exit',
                        'bars_held'            : (date - entry_date).days   
                    }
                )

                cash += proceeds
                position = 0

# ========================= ENTRY ===============
if position == 0 and row ['signal'] == 1 :
    risk_amount = cash * self.risk_per_trade
    stop_distance = self.atr_multiplier * atr

    if stop_distance > 0:
        shares = int(risk_amount /stop_distance)
        max_affordable = int(cash / (close * (1 + self.transaction_cost)))
        shares = min(shares, max_affordable)

        if shares > 0:
            cost = shares * close * (1 + self.transaction_cost)
            if cost <= cash:
                cash -+ cost
                positions = shares
                entry_price = close
                entry_date = date


       equity_list.append(cash + position * close)
    df['equity'] = equity_list
    df['buy_hold'] =(1 + df['close'].pct_change().fillna(0)).cumprod() *self.initial_capital
    
    self.data = df
    self.trades = pd.DataFrame(trade_log)
    return self

def performance_report(self)
    df = self.data.dropna(subset = ['equity']) 
    trades = self.trades

    final_equity = df['equity'].iloc[-1]
    total_return = (final_equity / self.intial_capital -1) * 100
    buy_hold_return = (df['buy_hold'].iloc[-1]  /self.initial_capital - 1) * 100 

    peak = df['equity'].cummax()
    dd = (df['equity'] - peak)  /peak
    max_dd = dd.min() * 100

    daily_ret = df['equity'].pct_change().dropna()
    sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() >0 else 0

    if len(trades) > 0:
        wins = trades[trades['pnl'] < 0]
        losses = traces[trade['pnl'] <= 0]
        win_rate = len(wins)  /len(trades) * 100
        avg_win = wins['return_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['return_pct'].mean() if len(losses) > 0 else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else np.inf
        avg_bars = trades['bars_held'].max()
        best = trades['return_pct'].max()
        worst = trades['return_pct'].min() 

    else:
        win_rate = avg_win = avg_loss = profit_factor = avg_bars = best = worst = 0

    print("\n" + "=" *70)
    print(f"ICHIMOKU CLOUD STRATEGY     -  {self.start} - {self.end}")
    print("=" * 70)
    print(f"period                      : {self.start} - {self.end}")
    print(f"Initial Capital             : ${self.initial_capital:,.0f}")
    print(f"Final Equity                : ${final_equity:,.2f}")
    print(f"Total Return                : {total_return:>10.2f}%")
    print(f"Buy & Hold Return           : {buy_hold_return:>10.2f}%")
    print(f"Max Drawdown                : {max_dd:>10.2f}%")
    print(f"Sharpe Ratio                : {sharpe:>10.2f}")
    print("-" * 70)
    print(f"Total Trades                : {len(trades)}")
    print(f"Win Trades                  : {win_rate:>10.1f}%")
    print(f"Average Win                 : {avg_win:>10.2f}%")
    print(f"Average Loss                : {avg_loss:>10.2f}%")
    print(f"Profit Factor               : {profit_factor:10.2f}")
    print(f"Avg Days Held               : {avg_bars:>10.1f}%")
    print(f"Best Trade                  : {best:>10.2f}%")
    print(f"Worst Trade                 : {worst:>10.2f}%")
    print("=" * 70)

    if len(trades) > 0:
        print("\nRecent Trades:")
        print(trades[['entry_date', 'exit_date', 'entry_price', 'exit_price','return_pct', 'reason']].tail(6).to_string(index=False))

def plot(self):
    df = self.data.dropna(subset=['senkou_a', 'equity']).copy()

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw ={'height_ratios': [2.8, 1.0, 1.3]})

    # ========= Price + Ichumoku Cloud ===========
    ax1 = axes[0]

    # Cloud
    ax1.fill_between(df.index, df['senkou_a'], df['senkou_b'],
                    where = df['senkou_a'] >= df['senkou_b'],
                    color = 'green', alpha=0.15, label='Bullish Cloud')
    ax1.fill_between(df.index, df['senkou_a'], df['senkou_b'],
                    where = df['senkou_a'], df['senkou_b'],
                    color = 'red', alpha=0.15, label='Bearish Cloud')

    ax1.plot(df.index, df['close'], label='Close', color='black', linewidth=1.3)
    ax1.plot(df.index, df['tenkan'], label='Tenkan (9)', color='blue', alpha=0.8)
    ax1.plot(df.index, df['kijun'], label='Kijun (26)', color='red', alpha=0.8)
    ax1.plot(df.index, df['senkou_a'], label='Senkou A', color='green', linestyle='--', alpha=0.6)
    ax1.plot(df.index, df['senkou_b'], label ='Senkou B', color='red', linestyle= '--', alpha=0.6)
    
    # Trade marker
    if len(self.trades) > 0:
        for _, t in self.trades.iterrows():
            ax1.scatter(t['entry_date'], t[entry_price], marker ='-', color='lime',
                        s = 120, edgecolors='black', zorder=5)
            ax1.scatter(t['exit_date'], t['exit_price'], marker ='_', color='red' 
                        s= 120, edgecolors='black', zorder=5) 

    ax1.set_title(f"{self.ticket} - Ichimoku Cloud Strategy", fontsize = 15)
    ax1.legend(loc ='upper left', fontsize = 9)
    ax1.grid(True, alpha=0.25)

    # ===== position visual ====
    ax2 = axes[1]
    ax2.fill_between(df.index, 0, 1, where= (df['close'] > df['cloud_top']),
                    color='green', alpha=0.35, label='Price Above Cloud') 
    ax2.fill_between(df.index, 0, 1, where=(df['close'] <df ['cloud_bottom']),
                    color='red', alpha=0.35, label='Price Below Cloud') 
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.25)

    # =============== Equity curve ===============
    ax3 = axes[2]
    ax3.plot(df.index, df['equity'], label='Strategy', color='navy', linewidth=1.7)
    ax3.plot(df.index, df['buy_hold'], label='Buy & Hold', color='darkorange', alpha=0.75)
    ax3.set_ylabel("Equity ($)")
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.25)

    plt.tight_layout()
    plt.show()

def run(self):
    (self.fetch_data()
         .add_ichimoku()
         .generate_signals()
         .run_backtest()
         .performance_report())
     self.plot()
     return self

# ======================================================================================
#  RUN
#  =====================================================================================
if __name__ == "__main__":

    strategy = IchimokuCloudStrategy(
        ticker="MSFT",
        start= "2015-02-02",
        end="2026-09-09",
        capital= 4000000,
        risk_per_trade = 0.01,
        atr_multiplier=2.5,
        transaction_cost=0.001
    )     

    strategy.run()




