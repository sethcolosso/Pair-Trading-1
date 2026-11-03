import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

class HeikinAshiEMAStrategy:
    def __init__(
        self,
        ticker="NVDA",
        start="2015-02-02",
        end="2026-05-05",
        capital= 250000,
        risk_per_trade=0.01,
        fast_ema=21,
        slow_ema=55,
        atr_period=14,
        atr_multiplier=2.0,
        transaction_cost=0.001,
        require_ha_consistency=3

    ):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_capital = capital
        self.risk_per_trade = risk_per_trade
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.transaction_cost = transaction_cost
        self.require_ha_consistency = require_ha_consistency

        self.data = None
        self.trades = []

    def fetch_data(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] downloading {self.ticker}....")
        df = yf.download(self.ticker, start=self.start, end=self.end, auto_adjust=True, progress=False)

        if isinstance(df.columns, pd.multiindex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        self.data = df
        print(f"Loaded {len(df)} bars| {df.index[0].date()} - {df.index[-1].date()}")
        return self

    def calculate_heikin_ashi(self, df):
        ha = pd.DataFrame(index=df.index)

        ha['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

        ha_open = [(df['open'].iloc[0] + df['close'].iloc[0]) / 2]
        for i in range (1, len(df)):
            ha_open.append((ha_open[i-1] + df['ha_close'].iloc[i-1]) /2)
        ha['ha_open'] = ha_open

        ha['ha_high'] = pd.concat([df['high'], ha['ha_open'], ha['ha_close']], axis=1).max(axis=1)
        ha['ha_low'] = pd.concat([df['low'], ha['ha_open'], ha['ha_close']], axis=1).min(axis=1)

        # Color: 1 =bullish (green), -1 = bearish(red)
        ha['ha_color'] = np.where(ha['ha_close'] >= ha['ha_open'], 1, -1)

        return ha

    def add_indicators(self):
        df = self.data.copy()

        # Heikin-Ashi
        ha = self.calculate_heikin_ashi(df)
        df = pd.concat([df, ha], axis=1)

        # EMAs on Heikin-Ashi close
        df['ema_fast'] = df['ha_close'].ewm(span=self.fast_ema, adjust=False).mean()
        df['ema_slow'] = df['ha_close'].ewm(span=self.fast_ema, adjust= False).mean()

        # ATR on normal price
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.atr_period).mean()


        # Consistency count (consecutive same color candles)
        df['ha_consistency'] = df['ha_color'].groupby(
            (df['ha_color'] != df['ha_color'].shift()).cumsum()
        ).cumcount()+1

        self.data = df
        return self

    def generate_signals(self):
        df = self.data.copy()

        # Trend Conditions
        bullish_ha = df['ha_color'] == 1
        bearish_ha = df['ha_color'] == -1
        ema_bullish = df['ema_fast'] > df['ema_slow']
        ema_bearish = df['ema_fast'] < df['ema_slow']

        # Strong entry : Heikin-Ashi bullish + EMA cross or already aligned + consistency
        long_entry = (
            bullish_ha &
            ema_bullish &
            (df['ha_consistency'] >= self.require_ha_consistency) &
            (df['ema_fast'] > df['ema_fast'].shift(1))

        )   


        # Exit when Heikin-Ashi bullish + EMA cross or already aligned + consistency
        long_entry = bearish_ha | ema_bearish

        df['signal'] = 0
        df.loc[long_entry, 'signal'] =1
        df.loc[long_exit, 'signal'] = -1
        
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

            if pd.isna(atr) or atr == 0 or pd.isna(row['ha_close']):
                equity_list.append(cash + position * close)
                continue

            # ============ EXIT =======
            if position > 0:
                if row['signal'] == -1:
                    exit_price = close
                    proceeds = position * exit_price (1 - self.transaction_cost)
                    pnl = proceeds - (position * entry_price)
                    pnl_pct = (exit_price / entry_price - 1) * 100

                    trade_log.append({
                        'entry_date'      : entry_date,
                        'exit_date'       : date,
                        'entry_price'     : round(entry_price, 2),
                        'exit_price'      : round(exit_price, 2),
                        'shares'          : position,
                        'pnl'             : round(pnl, 2),
                        'return_pct'      : round(pnl_pct, 2),
                        'reason'          : 'HA / EMA Exit',
                        'bars_held'       : (date- entry_date).days
                    })

                    cash += proceeds
                    position = 0

            # ================== ENTRY ========
            if position == 0 and row['signal'] == 1:
                risk_amount = cash * self.risk_per_trade
                stop_distance = self.atr_multiplier * atr

                if stop_distance > 0:
                    shares = int(risk_amount / stop_distance)
                    max_affordable = int(cash / (close * (1 + self.transaction_cost)))
                    shares = min(shares, max_affordable)

                    if shares > 0:
                        cost = shares * close * (1 + self.transaction_cost)
                        if cost <= cash:
                            cash -= cost
                            position = shares
                            entry_price = close
                            entry_date = date

            equity_list.append(cash + position * close)

        df['equity'] = equity_list
        df['buy_hold'] = (1 + df['close'].pct_change().fillna(0)).cumprod( *self.initial_capital)

        self.data = df
        self.trades = pd.DataFrame(trade_log)
        return self

    def performance_report(self):
        df = self.data.dropna(subset=['equity'])
        trades = self.trades

        final_equity = df['equity'].iloc[-1]
        total_return = (final_equity / self.initial_capital - 1) * 100
        buy_hold_return = (df['buy_hold'].iloc[-1] / self.initial_capiatal -1) * 100 

        peak = df['equity'].cummax()
        dd = (df['equity'] - peak) /peak
        max_dd = dd.min() * 100

        daily_ret = df['equity'].pct_change().dropna()
        sharpe = np.sqrt(252) * daily_ret.mean() / daily_-ret.std() if daily_ret.std() > 0 else 0

        if len(trades) > 0:
            wins = trades[trades['pnl'] > 0]
            losses = trades[trades['pnl'] <= 0]
            win_rate = len(wins) / len(trades) * 100
            avg_win = wins['return_pct'].mean() if len(wins) > 0 else 0
            avg_loss = losses['return_pct'].mean() if len(losses) > 0 else 0
            profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() ! = 0 else np.inf
            avg_bars = trades['bars_held'].mean()
            best = trades['return_pct'].max()
            worst = trades['return_pct'].min()
        else:
            win_rate = avg_win = avg_loss = profit_factor = avg_bars = best = worst = 0

        print("\n" + "=" * 70)
        print(f"HEIKIN-ASHI + DUAL EMA STRATEGY {self.ticker}")
        print("=" * 70)
        print(f"period                         : {self.start} - {self.end}")
        print(f"Initial Capital                : ${self.initial_capital:,.0f}")
        print(f"Final Equity                   : ${self.equity:,.2f}")
        print(f"Total Return                   : {total_return:>10.2f}%")
        print(f"buy & Hold Return              : {buy_hold_return:>10.2f}%")
        print(f"Max Drawdown                   : {max_dd:>10.2f}%")
        print(f"Sharpe Ratio                   : {sharpe:>10.2f}") 
        print("-" * 70)
        print(f"Total Trades                   : {len(trades)}")
        print(f"Win Rate                       : {win_rate:>10.1f}%")
        print(f"Average Win                    : {avg_win:>10.2f}%")
        print(f"Average Loss                   : {avg_loss:>10.2f}%")
        print(f"Profit Factor                  : {profit_factor:>10.2f}")
        print(f"Avg Days Held                  : {avg_bars:>10.1f}%")
        print(f"Worst Trade                    : {worst:>10.2f}%")
        print(f"Best Trade                     : {best:>10.2f}%")
        print("=" * 70)

        if len(trades) > 0:
            print("\nRecent Trades:")
            print(trdes[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'reason' ]].tail(6).to_string(index= False))


    def plot(self):
        df = self.data.dropna(subset=['ha_close','equity'])

        fig, axes = plt.subplots(4,1, figsize=(16, 14), gridspec_kw={'height_ratios':[2.4, 0.9, 0.9, 1.3]})


        # ============ Heikin-Ashi style price chart =========
        ax1 = axes[0]

        # plot normal close for reference
        ax1.plot(df.index, df['close'], color='gray', alpha 0.4, linewidth=1, label='Normal Close')

        # plot Heikin-Ashi close
        ax1.plot(df.index, df['ha_close'], color='black',linewidth=1.3, label='Heikin-Ashi Close')

        # Color background by HA direction
        ax1.fill_between(df.index, df['ha_low'], df['ha_high'], where= df['ha_color'] == 1, color='green', alpha=0.15)
        ax1.fill_between(df.index, df['ha_low'], df['ha_high'], where=df['ha_color'] == -1, color='red', alpha=0.015)
        ax1.plot(df.index, df['ema_fast'], label= f'EMA {self.fast_ema}', color='blue', alpha=0.8)
        ax1.plot(df.index, df['ema_slow'], label=f'EMA {self.slow_ema}', color='orange', alpha=0.8)

        if len(self.trades) > 0:
            for _, t in self.trades.iterows():
                ax1.scatter(t['entry_date'], t['entry_price'], marker='-', color='lime', s= 120, edgecolors='black', zorder=5)
                ax1.scatter(t['exit_date'], t['exit_price'], marker='_', color='red', s= 120, edgecolors='black', zorder=5)

        ax1.set_title(f"{self.ticker} - Heikin-Ashi + Dual  EMA Strategy", fontsize=15)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.25)

        # HA Color
        ax2 = axes[1]
        ax2.fill_between(df.index, 0, 1, where=df['ha_color'] == 1, color='green', alpha=0.4, label='Bullish HA')
        ax2.fill_between(df.index, 0, 1, where=df['ha_color'] ==-1, color='red', alpha=0.3, label='Bearish HA')
        ax2.set_ylim(-0.1, 1.1)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.25)

        # EMA relationship
        ax3 = axes[2]
        ax3.fill_between(df.index, 0, 1, where =df['ema_fast']>df['ema_slow'], color='blue', alpha=0.3, label='Fast EMA > slow EMA')
        ax3.set_ylim(-0.1, 1.1)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.25)

        # Equity
        ax4 = axes[3]
        ax4.plot(df.index, df['equity'], label='Strategy', color='navy', linewidth =1.7)
        ax4.plot(df.index, df['buy_hold'], label='Buy & Hold', color='darkorange', alpha=0.75)
        ax4.set_ylabel("Equity ($)")
        ax4.legend(loc='upper left')
        ax4.grid(True, alpha=0.25)

        plt.tight_layout()
        plt.show()

    def run(self):
        (self.fetch_data()
             .add_indicators()
             .generate_siganla()
             .run_backtest()
             .performance_report())
         self.plot() 
         return self

       # =============================================================================
       #  RUN
       # =============================================================================
if __name__ == "__main__":

    strategy = HeikinAshiEMAStrategy(
        ticker = "TSLA",
        start = "2015-09-09"
        end = "2026-07-07"
        capital = 250000,
        risk_per_trade = 0.01,
        fast_ema = 21,
        slow_ema = 55,
        atr_period = 14,
        atr_multiplier = 2.0,
        require_ha_consistency = 3,
        transaction_cost = 0.001
    )  

    strategy.run()      


                   