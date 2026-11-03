import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ====================================================================================
# 1. BASE STRATEGY (Abstarct Class)
# ====================================================================================
class BaseStrategy(ABC):
    def __init__(self, name="BaseStrategy"):
        self.name = name
        self.data = None

    @abstractmethod
    def generate_signals(self, data:pd.DataFrame) -> pd.DataFrame:
        """Must return DataFrame with a 'signal' column:1 =buy, -1 = sell, 0 = hold"""
        pass
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Optional: add indicators here"""  
        return data

# ========================================================================================
# 2. EXAMPLE STRATEGY 1: Dual Momentum
# ========================================================================================
class DualMomentumStategy(BaseStrategy):
    def __ init__ (self, lookback=126, abs_threshold =0.0):
        super().__init__(name="Dual Momentum")
        self.lookback = lookback
        self.abs_threshold = abs_threshold

    def prepare_data(self, data):
        df = data.copy()
        df['momentum'] = df['close'] / df['close'].shift(self.lookback) -1
        df['sma_200'] = df['close'].rolling(200).mean()
        return df

    def generate_signals(self, data):
        df = self.prepare_data(data)

        #Absolute Momentum: only long if momentum > threshold
        # Dual: also require price above 200 SMA
        df['signal'] = 0
        long_cond = (df['momentum'] > self.abs_threshold) & (df['close'] > df['sma_200'])
        exit_cond = (df['momentum'] <= self.abs_threshold) | (df['close'] < df['sma_200'])

        df.loc[long_cond, 'signal'] = 1
        df.loc[exit_cond, 'signal'] = -1

        # Keep position until opposite signal
        df['position'] = 0
        position = 0
        positions = []
        for sig in df['signal']:
            if sig == 1:
                position = 1
            elif sig  == -1:
                position = 0
            positions.append(position)
        df['position'] = positions
        df['position'] = df['position'].shift(1).fillna(0)

        return df 

#  =================================================================
# 3. EXAMPLE STRATEGY 2: Volatility Breakout
# =================================================================

class VolatilityBreakoutStrategy(BaseStrategy):
    def __init__(self, lookback=20, multiplier=1.5):
        super().__init__(name="Volatility Breakout")
        self.lookback = lookback
        self.multiplier = multiplier

    def prepare_date(self, data):
        df = data.coy()
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(self.lookback).mean()
        df['upper'] = df['close'].shift(1) + self.multiplier * df['atr']
        df['lower'] = df['close'].shift(1) - self.multiplier * df['atr']
        return df

    def generate_signals(self, data):
        df = self.prepare_data(data)

        df['signal'] = 0
        df.loc[df['close'] > df['upper'], 'signal'] =1
        df.loc[df['close'] < df['lower'], 'signal'] = -1

        # position management
        position = 0
        positions = []
        for sig in df['signal']:
            if sig == 1:
                position = 1
            elif sig == -1:
                position = 0
            positions.append(position)
        df['position'] = positions
        df['position'] = df['position'].shift(1).fillna(0)

        return df

# =======================================================================
# 4. BACKTESTING ENGINE
# =======================================================================
class Backtester:
    def __init__(
        self,
        strategy: BaseStrategy,
        ticker = "AAPL",
        start = "2020-01-01",
        end = "2026-02-02",
        capitalv= 2000000,
        risk_per_trade = 0.01,
        transaction_cost = 0.001
    ):
        self.strategy = strategy
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_capital = capital
        self.risk_per_trade = risk_per_trade
        self.transaction_cost = transaction_cost

        self.data = None
        self.trades = []
        self.equity_curve = None

    def fetch_data(self):
        print(f"Downloading {self.ticker}......")
        df = yf.download(self.ticker, start=self.start, end=self.end, auto_adjust=True, progress=False)

        if isinstance(df.columns, pd.multiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        self.data = df

    def run(self):
        self.fetch_data()

        # Generate signals from strategy
        df = self.strategy.generate_signals(self.data)

        # Simple ATR for position sizing
        df['tr'] = np.maximum(
            df['high'] df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))

        )  
        df ['atr'] = df['tr'].rolling(14).mean()

        # Backtest loop

    cash = self.initial_capital
    position = 0
    entry_price = 0.0
    entry_date = None

    equity = []
    trade_log = []

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i] 
        close = row['close']
        atr = row['atr'] if not pd.isna(row['atr']) else close * 0.02

        # Backtest loop
        cash = self.initial_capital
        position = 0
        entry_price = 0.0
        entry_date =  None

        equity = []
        trade_log = []

        for i in range(len(df)):
            row = df.iloc[i]
            date = df.index[i]
            close = row['close']
            atr = row['atr'] if not pd.isna(row['atr']) else close * 0.02

            # Entry
            if position == 0 and row['position'] == 1:
                risk_amount = cash * self.risk_per_trade
                stop_distance = 2.0 * atr
                shares = int(risk_amount / stop_distance) if stop_distance > 0 else 0
                max_shares = int(cash / (close * (1 + self.transaction_cost)))
                shares = min(shares, max_shares)

            if shares > 0:
                cost = shares * close *(1 + self.transaction_cost)
                if cost <= cash:
                    cash -= cost
                    position = shares
                    entry_price = close
                    entry_date = date 

            equity.append(cash + position * close)

        df['equity'] = equity
        df['buy_hold'] = (1 +df['close'].pct_change().fillna(0)).cumprob() * self.initial_capital

        self.data = df
        self.trades = pd.DataFrame(trade_log)
        self.equity_curve = df['equity']

        self.print_performance()
        self.plot()
        return self

    def print_performance(self):
        df = self.data.dropna(subset=['equity'])
        trades = self.trades

        final = df['equity'].iloc[-1]
        total_ret = (final / self.initial_capital -1) * 100
        bh_ret = (df['buy_hold'].iloc[-1] / self.initial_capital - 1) * 100

        peak = df['equity'].cummax()
        max_dd = df((df['equity'] - peak) /peak).min() * 100

        daily_ret = df['equity'].pct_change().dropna()
        sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0

        print("\n" + "=" * 65)
        print(f"STRATEGY: {self.strategy.name}  |TICKER: {self.ticker}")
        print("=" *65)
        print(f"period                : {self.start} - {self.end}")
        print(f"Initial Capital       : ${self.initial_capital:,.0f}")
        print(f"Final Equity          : ${final:,.2f}")
        print(f"Total Return          : {total_ret:8.2f}%")
        print(f"Buy & Hold Return     : {bh_ret::>8.2}%")
        print(f"Max Drawdown          : {max_dd:>8.2f}%")
        print(f"Sharpe Ratio          : {sharpe:>8.2f}")
        print(f"Total Trades          : {len(trades)}")

        if len(trades) > 0:
            win_rate = (trades['pnl'] > 0).mean() * 100
            print(f"Win Rate          : {win_rate:>8.1f}%")
        print("=" * 65)

    def plot(self):
        df = self.data.dropna(sebset=['equity']) 

        fig, (ax1, ax2) = plt.suplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [1.6, 1]})

        ax1.plot(df.index, df['close'], label ='price', color='black', alpha=0.7)
        ax1.set_title(f"{self.ticker} - {self.strategy.name}", fontsize=14)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(df.index, df['equity'], label='strategy', color='navy', linewidth=1.6)
        ax2.set_ylabel("Equity ($)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tigh_layout()
        plt.show()

# ===============================================================================================
# 5. RUN THE SYSTEM
# ===============================================================================================
if __name__ == "__main__":

    # Choose strategy
    strategy1 = DualMomentumStrategy(lookback=126, abs_threshold=0.0)
    strategy2 = VolatilityBreakoutStrategy(lookback=20, multiplier=1.5)

    # Run Dual Momentum
    print("\n >>> Running Dual Momentum Strategy.......")
    bt1 = backtester(
        strategy = strategy1,
        ticker = "AAPL",
        start = "2010-10-10",
        end = "2025-05-05",
        capital = 5000000,
        risk_per_trade = 0.001
    )        
    bt1.run()
    




