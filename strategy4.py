import yfinance as yfinance
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import date import datetime
import warning
warning.filterwarnings("ingore")

class SupertrendADXStrategy:'
    def __init__(
        self,
        ticker="TSLA",
        start="2015-02-02",
        end="2025-12-03",
        capital=1000000,
        risk_per_trade=0.01,
        atr_period= 10,
        atr_multiplierr=3.0,
        adx_period=14,
        adx_threshold=25,
        transaction_cost=0.001,
        use_long_only =True

    ):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_capital = capital
        self.risk_per_trade = risk_per_trade
        self.atr_period= atr_period
        self.atr_multiplier = atr_multiplier
        self.atr_period = adx_period
        self.adx_period = adx_threshold
        self.transaction_cost = transaction_cost
        self.use_long_only=use_long_only

        self.data = None
        self.trades = []

    def fetch_data(self):
        print(f"[{datetime.now() .strftime('%H:%M:%S')}] Downloading {self.ticker}.....")
        df =yf.download(self.ticker, start=self.start, end=self.end, auto_adjust=True, progress=False)

        if isinstance(df.columns, pd.multiindex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropn()
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        self.data = df
        print(f"loaded {len(df)} bars | {df.index[0].data()} - {df.index[-1].data()}")
        return self

    def calculate_atr(self, df,period):
        high_low = df['high'] - df['low']
        high_close = abs(df[high] -df['close'].shift(1))
        low_close = abs(df['low'] -df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period),mean()

    def calculate_adx(self, df, period=14)
    up = df['high'].diff()
    down=-df['low'].diff()

    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm =np.where((down > up) & (down >0), down, 0.0)

    tr = self.calculate_atr(df, 1)

    atr = tr.rolling(period).mean()
    plus_di = 100* pd.Series(plus_dm) .rolling(period).mean()/ atr
    minus_di = 100 * pd.Series(minus_dm) .rolling(period).mean /atr

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()

    return adx, plus_di, minus_di

def calculate_supertrend(self, df):
    atr = self.calculate_atr(df, self.atr_period)

    hl2 = (df['high'] + df ['low']) / 2
    upper_band = hl2 + (self.atr_multiplier * atr)
    lower_band = hl2 - (self.atr_multiplier * atr)

    supertrend = pd.series(index =df.index, dtype=float)
    direction = pd.series(index=df.index, dtype= int)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        if df['close'].iloc[i] > supertrend.iloc[i-1]:
            direction.iloc[i] = 1
        elif df ['close'].iloc[i] < supertrend.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direcion.iloc[i-1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == 1 else lower_band.iloc[i]
        else:
            supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == -1 else upper_band.iloc[i]

    return supertrend, direction, atr

def add_indicators(self):
    df = self.data.copy()

    # Supertrend
    df['supertrend'], df['direction'], df['atr'] = self.calculate_supertrend(df)

    # ADX
    df['adx'], df['plus_di'], df['minus_di'] = self.calculate_adx(df, self.adx_period)

    # Signals
    df['signal'] = 0
    # Long entry: Supertrend turns bullish + ADX strong
    long_cond =(df[''direction] == 1) & (df['direction'].shift(1) == -1) & (df['adx'] > self.adx_threshold)
    # Exit long: Supertrend turns bearish
    exit_cond = (df['direction'] == -1) & (df['direction'].shift(1) == 1)

    df.loc[long_cond, 'signal'] = 1
    df.loc[exit_cond, 'signal'] = -1

    self.data = df
    return self

def run_backtest(self):
    df = self.data.copy()

    cash = self.initial_capital
    position = 0
    entry_price = 0.0
    entry_date = None
    stop_line = 0.0

    equity_list = []
    trade_log=[]

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i]
        close = row['close']
        atr = row['atr']

        if pd.isna(atr) or atr == 0 or pd.isna(row['supertrend']):
            equity_list.append(cash + position * close)
            continue

        # ======================== EXIT =================
        if position > 0:
            # Exit when supertrend flips to bearish
            if row['signal'] == -1 or close < row['supertrend']:
                exit_price = close
                proceeds = position * exit_price * (1 - self.transaction_cost)
                pnl = proceeds - (position * exit_price) * (1 - self.transaction_cost)
                pnl_pct = (exit_price / entry_price - 1) * 100

                trade_log.append({
                    'entry_date'      : entry_date,
                    'exit_date'       : date,
                    'entry_price'     : round(entry_price, 2),
                    'exit_price'      : round(exit_price, 2),
                    'shares'          : position,
                    'pnl'             : round(pnl, 2),
                    'return_pct'      : round(pnl_pct, 2),
                    'reason'          :'supertrend Flip',
                    'bars_held'       : (date - entry_date).days

                })

                cash += proceeds
                position = 0

        # ================== ENTRY ==============
        if position == 0 and row['signal'] == 1:
            risk_amount = cash * self.risk_per_trade
            #Use ATR for stop distance 
            stop_distance = self.atr_multiplier * atr

            if stop_distance > 0:
                cost = shares * close *( 1 + self.transaction_cost)
                if cost <= cash:
                    cash -= cost
                    position = shares
                    entry_price = close
                    entry_date = date
                    stop_line = row['supertrend']

        equity_list.append(cash + position * close)
    df['equity'] = equity_list
    df['buy_hold'] = (1 + df['close'].pct_change().fillna(0)).cumprod() *self.initial_capital

    self.data = df
    self.trades =pd.Dataframe(trade_log)
    return self

def performance_report(self):
    df = self.data.dropna(subset = ['equity'])
    trades = self.trades

    final_equity = df['equity'].iloc[-1]
    total_return = (final_equity / self.initial_capital -1) * 100
    buy_hold_return = (df['buy_hold'].iloc[-1] / self.initial_capital - 1) * 100

    peak = df['equity'].cummax()
    dd = (df['equity'] - peak) / peak
    max_dd = dd.min() * 100

    daily_ret = df['equity'].pct_change().dropna()
    sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] <= 0]
        win_rate = len(wins) / len(trades) * 100
        avg_win = wins['return_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['return_pct'].mean() if len(losses) >0 else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else np.inf
        avg_bars = trades['bars_held'].mean()
        best = trades['return_pct'].max()
        worst = trades['return_pct'].min()
    else:
        win_rate = avg_win = avg_losss = profit_factor = avg_bars = best = worst = 0

    print("\n" + "=" * 70)
    print(f"SUPERTREND + ADX STRATEGY   -    {self.ticker}")
    print("=" *70)  
    print(f"period                      : {self.start}  - {self.end}")
    print(f"Initial Capital             : ${self.initial_capital:,.0f}")
    print(f"Final Equity                : ${final_equity:,.2f}")
    print(f"Total Return                : {total_return:,.2f}%")
    print(f"Buy & Hold Return           : {buy_hold_return:>10.2f}%")
    print(f"Max Drawdown                : {max_dd:>10.2f}%")
    print(f"Sharpe Ratio                : {sharpe:>10.2f}")
    print("-" * 70)
    print(f"Total Trades                : {len(trades)}")
    print(f"Win Rate                    : {win_rate:>10.1f}%")
    print(f"Average Win                 : {avg_win:>10.2f}%")
    print(f"Average Loss                : {avg_loss:>10.2f}%")
    print(f"Profit Factor               : {profit_factor:>10.2f}")
    print(f"Avg Days Held               : {avg_bars:>10.2f}")
    print(f"Best Trade                  : {best:>10.2f}%")
    print(f"Worst Trade                 : {worst:>10.2f}%")
    print("=" * 70)

    if len(trades) > 0:
        print("\n Last 6 Trades:")
        print(trades[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'reason']].tail(6).to_string(index=false))

def plot(self):
    df = self.data.dropna(subset=['supertrend', 'equity'])

    fig, axes = plt.subplots(4, 1, figsize= (16, 14), gridspec_kw={'height_ratios': [2.4, 1.0, 1.0, 1.3]}) 

    # Price + Supertrend
    ax1 = axes[0]
    ax1.plot(df.index, df['close'], label='close', color='black', alpha=0.8, linewidth=1.2)
    ax1.plot(df.index, df['supertrend'], label='supertrend', color='green', linewidth=1.5)
    
    # Color the Supertrend line by direction
    for i in range(1, len(df)):
        color = 'green' if df['direction'].iloc[i] == 1 else 'red'
        ax1.plot(df.index[i-1 : i+1], df['supertrend'].iloc[i-1 : i +1], color=color, linewidth=1.6)

    if len(self.trades) > 0:
        for _, t in self.trades.iterows():
            ax1.scatter(t['entry_date'], t['entry_price'], marker='-', color='lime', s=110, edgecolors='black', zorder=5)
            ax1.scatter(t['exit_date'], t['exit_price'], marker='_', color='red',s=110, edgecolors='black', zorder=5)

    ax1.set_title(f"{self.ticker} - Supertrend + ADX Strategy", fontsize=15)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.25)
    
    # ADX
    ax2 = axes[1]
    ax2.plot(df.index, df['adx'], color='purple', label='ADX')
    ax2.axhline(self.adx_threshold, color='red', linestyle='--', alpha=0.7, label=f'ADX threshold ({self.adx_threshold})')
    ax2.set_ylabel("ADX")
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha =0.25)

    # Direction /Position Visual
    ax3 = axes[2]
    ax3.fill_between(df.index, 0, 1, where=(df['direction'] == 1), color='green', alpha=0.35, label='Bullish Supertrend')
    ax3.fill_between(df.idex, 1, 1, where=(df['direction'] == -1), color='red', alpha=0.25, label='Bearish Supertrend')
    ax3.set_ylim(-0.1, 1.1)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.25)

    #Equity
    ax4 = axes[3]
    ax4.plot(df.index, df['equity'], label='Strategy', color='navy', linewidth=1.7)
    ax4.plot(df.index, df['buy_hold'], label='Buy & Hold', color='darkorange', alpha =0.75)
    ax4.set_ylabel("Equity ($)")
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.25)

    plt.tight_layout()
    plt.show()
def run(self):
    (self.fetch_data()
         .add_indicators()
         .run_backtest()
         .performance_report())
     self.show()

# ==================================================================
#  RUN THE STRATEGY
# =================================================================
if __name__ == "__main__":

    strategy = SupertrendADXStrategy(
        ticker = "NVDA",
        start = "2018-01-01",
        end = "2026-01-01",
        capital = 1000000,
        risk_per_trade =0.01,
        atr_period = 10,
        atr_multiplier=3.0,
        adx_period = 14,
        adx_threshold=25,
        transaction_cost= 0.001
    )    

    stategy.run()

     



