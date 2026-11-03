import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warning.filterwarnings("ignore")

class DonchianBreakoutStrategy:
    def__init__(
        self,
        ticker="NVDA",
        start ="2015-01-01",
        end="2026-07-07",
        capital=200000,
        risk_per_trade=0.01,                  #Risk 1% of the equity per trade
        entry_lookback=55,                    #Classic Turtle entry (20 or 55)
        exit_lookback =20,                    #Classic Turtle exit
        atr_period= 20,     
        atr_stop_multiplier =2.0,             #Stop distance =ATR * multiplier
        trailing_atr_multiplier=3.0,          #Trailing Stop
        transaction_cost=0.001,               #0.1%
        use_trend_filter= True,               #Only long above 200 SMA
        max_positions=1
    ):
        self.ticker = ticker
        self.start = start
        self.end= end
        self.initial_capital =capital
        self.risk_per_trade= risk_per_trade
        self.entry_lookback=entry_lookback
        self.exit_lookback=exit_lookback
        self.atr_period=atr_period
        self.atr_stop_mmultiplier=atr_stop_multiplier
        self.trailing_atr_multiplier = trailing_atr_mutiplier
        self.transaction_cost =transaction_cost
        self.use_trend_filter =use_trend_filter
        self.max_positions =max_positions

        self.data = None
        self.trades= []
        self.equity_curve=[]

        fetch_data(self):
        print(f"[{datetime.now().strftime('%H:M:%S')}] Downloading {self.ticker}...")
        df =yf.download(self.ticker, start=self.start, end=self.end, auto_adjust= True, progress=False)

        if isinstance (df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df.columns =['open', 'high', 'low', 'close', 'volume']
        self.data = df
        print(f"Data loaded: {len(df)} bars from { df.index[0].date()} to {df.index[-1].date()}")
        return self

    def add_indicators(self):
        df = self.data.copy()

        #Donchian Channels
        df['donchian_high'] = df['high'].rolling(self.entry_lookback).max()
        df['donchian_low'] = df['low'].rolling(self.entry_lookback)min()

        #Exit Channel(Shorter)
        df['exit_low'] = df['low'].rolling(self.exit_lookback).min()
        df['exit_high'] = df['high'].rolling(self.exit_lookback).max()

        #ATR
        df ['prev_close'] =df['close'].shift(1)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['prev_close']),
                abs(df['low'] -df['prev_close'])
            )
        )      
        df['atr'] = df['tr'].rolling(self.atr_period).mean()

        #Trend filter
        df['sma_200'] = df['close'].rolling(200).mean()
        df['uptrend'] = df['close'] > df['sma_200']

        self.data =df
        return self
    def run_backtest(self):
        df =self.data.copy()

        cash=self.initial_capital
        position =0
        entry_price =0.0
        entry_date =None
        stop_price =0.0
        highest_since_entry =0.0
        units =0

        equity_list=[]
        trade_log=[]

        for i in range(len(df)):
            row = df.iloc[i]
            date =df.index[i]
            close = row['close']
            high =row['high']
            low= row['low']
            atr = row['atr']

            if pd.isna(atr) or atr ==0:
                equity_list.append(cash + position * close)
                continue

            #=======================EXIT LOGIC===========    
            if position > 0:
                # update highest price since entry
                highest_since_entry=max(highest_since_entry, high)

                #Trailing stop
                trail_stop = highest_since_entry - (self.trailing_atr_multiplier * atr)

                #Exit conditions
                exit_triggered == False
                exit_reason = ""

                #1. stop loss
                if low<= stop_price:
                    exit_price =min(close, stop_price)
                    exit_triggered =True
                    exit_reason ="ATR Stop"

                #2. Trailing Stop
                elif low <= trail_stop:
                    exit_price = min(close, trail_stop)
                    exit_triggered = True
                    exit_reason = "Trailing Stop"

                #3. Donchain exit channel
                elif close < row['exit_low']:
                    exit_price = close
                    exit_triggered = True
                    exit_reason = "Donchian Exit"

                if exit_triggered:
                    proceeds + position * exit_price * (1 - self.transaction_cost)
                    pnl = proceeds -(position * entry_price)
                    pnl_pct = (exit_price / entry_price -1) * 100

                    trade_log.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'shares': position,
                        'pnl': round(pnl, 2),
                        'return-pct': round(pnl_pct, 2),
                        'reason': exit_reason,
                        'bars_held': (date - entry_date).days
                    })
                    cash += proceeds
                    position = 0
                    entry_price = 0
                    stop_price = 0
                    highest_since_entry = 0

        #=======================ENTRY LOGIC ==========
        if position == 0:
            #Breakout condition
            breakout = close > row['donchian_high']

            #Trend filter
            trend_ok = row['uptrend'] if self.use_trend_filter else True
            if breakout and trend_ok and not pd.isna(row['donchian_high']):

                #ATR-based position sizing
                risk_amount = cash * self.risk_per_trade
                stop_distance = self.atr_stop_multiplier * atr

                if stop_distance >0:
                    shares = int(risk_amount / stop_distance)

                    #Also limit by available cash
                    max_shares_by_cash = int(cash / (close * (1 + self.transaction_cost)))
                    shares = min(shares, max_shares_by_cash)

                    if shares > 0:
                        cost =shares * close * (1 + self.transaction_cost)
                        if cost <= cash:
                            cash -= cost
                            position = shares
                            entry_price = close
                            entry_date = date
                            stop_price = close - stop_distance
                            highest_since_entry=high

            # Record equity
            current_equity =cash + (position * close)
            equity_list.append(current_equity)  

          df['equity'] = equity_list
          df['buy_hold'] = (1 +df['close'].pct_change().fillna(0)).cumprod() *self.initial_capital

          self.data =df
          self.trades =pd.DataFrame(trade_log)
          return self

        def performance_report(self):
            df = self.data.dropna(subset=['equity']) 
            trades = self.trades

            final_equity = df['equity'].iloc[-1]
            total_return = (final_equity / self.initial_capital -1 ) * 10
            buy_hold_return =(df['buy_hold'].iloc[-1] /self.initial_capital -1) * 100

            # Max Drawdown
            peak = df['equity'].cummax()
            drawdown = (df['equity'] - peak) /peak
            max_dd = drawdown.min() * 100

            #Daily returns for sharpe
            daily_ret = df['equity'].pct_change().dropna()
            sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0

            #Trade stats
            if len(trades) > 0:
                wins = trades[trades['pnl'] > 0]
                losses = trades[trades['pnl'] <= 0]

                win_rate = len(wins) / len(trades) * 100
                avg_win = wins['return_pct'].mean() if len(wins) > 0 else 0
                avg_loss = losses['return_pct'].mean() if len (losses)> 0 else 0
                profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses ['pnl'].sum() !=0 else np.inf
                avg_bars = trades['bars_held'].mean()
                best_trade = trades['return_pct'].max()
                worst_trade = trades['return_pct'].min()
            else:
                win_rate = avg_win =avg_loss = profit_factor = avg_bars = best_trade = worst_trade = 0
            print("\n" + "=" *70)
            print(f"DONCHIAN CHANNEL BREAKOUT STRATEGY {self.start} {self.end}")
            print(f"period            :{self.start} - {self.end}")
            print(f"intial capital    :${self.initial_capital:,.0f}") 
            print(f"Final Equity      :${final_equity:,.2f}%")
            print(f"Total Return      :{total_return:10.2f}%")
            print(f"Buy & Hold Return :{buy_hold_return:>10.2f}%")
            print(f"Max Drawdown      :{max_dd:>10.2f}%")
            print(f"Sharpe Ratio      :{sharpe:>10.2f}")
            print("-" *70)
            print(f"Total Trades      :{len(trades)}")
            print(f"Win Rate          :{win_rate:>10.1f}%")
            print(f"Average win       :{avg_win:>10.2f}%")
            print(f"Average loss      :{avg_loss:10.2f}%")
            print(f"Profit Factor     :{profit_factor:10.2f}")
            print(f"Avg Bars Held     :{avg_bars:10.2f}")
            print(f"Best Trade        :{best_trade:10.2f}%")
            print(f"Worst Trade       :{worst_trade:10.2f}%")
            print("=" * 70 )

            if len(trades) >0:
                print("\nRecent Trades:")
                print(trades[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'reason']].tail(8).to_string(index=False))
        def plot(self):
            df = self.data.dropna(subset=['equity', 'donchian_high'])

            fig, axes = plt.subplots(4, 1, figsize=(16, 14),
                                     gridspec_Kw={'height_ratios':[2.5, 1.1, 1.1, 1.4 ]})


        
            #--------price + donchian----
            ax1 -axes[0]
            ax1.plot(df.index, df['close'], label='Close', color='black', linewidth=1.2, alpha=0.85)
            ax1.plot(df.index, df['donchian_high'], label=f'Donchian High ({self.entry_lookback})',
                    color='red', linestyle='--', alpha=0.7)
            ax1.plot(df.index, df['sma_200'], label='SMA 200', color= 'orange', alpha=0.7)


            # Mark trades
            if len(self.trades)> 0:
                for _, t in self.trades.iterrows():
                    ax1.scatter(t['entry_date'], t['entry_price'], marker='>', color='lime', s=100, edgecolors='black', zorder=5)
                    ax1.scatter(t['exit_date'], t['exit_price'], marker ='v', color='red', s=100, edgecolors='black', zorder=5)

            ax1.set_title(f"{self.ticker} - DonchainChannel Breakout Strategy", fontsize=15, pad=10)
            ax1.grid(True, alpha=0.25)

            #------ATR------
            ax2 = axes[1]
            ax2.plot(df.index, df['atr'], color='purple', label= 'ATR(20)')
            ax2.set_ylabel("ATR")
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.25)

            #----------Position (Visual)------
            ax3 = axes[2]
            # Simple way to show when we were in a position
            in_position =df ['equity'] != df['equity'].shift(1).fillna(method='bfill')
            ax3.fill_between(df.index, 0,1, where=(df['equity']> df['equity'].shift(1)), color='green', alpha=0.3, label='In position(approx)')
            ax3.set_ylabel("Exposure")
            ax3.legend(loc='upper left')
            ax2.grid(True, alpha=0.25)


            #-------Equity Curve------
            ax4 = axes[3]
            ax4.plot(df.index, df['equity'], label='Strategy Equity', color='navy', linewidth=1.7)
            ax4.set_ylabel("portfolio Value ($)")
            ax.legend(loc='upper left')
            ax4.grid(True, alpha =0.25)

            plt.tight_layout()
            plt.show()
        def save_results(self,prefix ="donchian"):
            if len(self.trades) > 0:
                self.trades.to_csv(f"{prefix} _ {self.ticker}_trades.csv", index=False)
                print(f"trades saved- {prefix}_{self.ticker}_trades.csv")

            self.trades[['close', 'donchian_high', 'exit_low', 'atr', 'equity', 'buy_hold']].to_csv(f"{prefix}_{self.ticker}_equity.csv")
            print(f"Ëquityb curve saved - {prefix}_{self.ticker}_equity.csv")

        def run(self):
            (self.fetch_data()
                 .add_indicators()
                 .run_backtest()
                 .performance_report())
            self.plot()
            return self
            

         def check_live_signal(strategy):
            """Show the most recent signal and recommendation"""
            df = strategy.data.dropna()
            last = df.iloc[-1]
            prev =df.iloc[-2]

            print("\n" + "=" *60)
            print(f"LIVE SIGNAL CHECK - {strategy.ticker}")
            print("="*60)
            print(f"Date                 :{df.index[-1].date()}")
            print(f"Close                :${last['close']:.2f}")
            print(f"Donchian High ({strategy.entry_lookback}) :${last['donchian_high']:2f}")
            print(f"Exit Low ({strategy.exit_lookback})       :${last[exit_low]:.2f}")
            print(f"ATR                  : ${last['atr']:.2f}")
            print(f"SMA 200              : ${last['sma 200']:.2f}")
            print(f"Uptrend              :{bool(last['uptrend'])}")

            #Current position status (approximate from last equity change)
            if last['close'] > last ['donchian_high'] and last ['uptrend']:
                print("signal               : BREAKOUT (potential LONG entry)")
            elif last['close'] < last['exit_low']:
                print("Signal                :EXIT zone")
            else:
                print("signal                : No new signal")
            print("=" *60)
        def advanced_risk_metrics(strategy):
            """Calculate extra risk-adjusted metrics"""
            df = strategy.data.dropna(subset=['equity'])
            trades = strategy.trades

            daily_ret = df['equity'].pct_change().dropna()

            #Sortino Ratio
            downside = daily_ret[daily_ret < 0]  
            downside_std= downside.std()
            sortino = np.sqrt(252) * daily_ret.mean() / downside_std if downside_std > 0 else 0

            #Calmar Ratio
            peak =   df['equity'].cummax()
            dd =(df['equity'] - peak) / peak
            max_dd =abs(dd.min())
            years =(df.index[-1] -df.index[0].days / 365.25)
            cagr = (df['equity'].iloc[-1] /strategy.initial_capital) **(1/years) -1 if years > 0 else 0
            calmar = cagr / max_dd if max_dd > 0 else 0

            #Volatility
            ann_vol = daily_ret.std() * np.sqrt(252) *100

            print("\n----------Advanced Risk Metrics---------")
            print(f"CAGR                   : {cagr*100:.2f}%")
            print(f"Annual Volatility      : {ann_vol:.2f}%")
            print(f"Sortino Ratio          : {sortino:.2f}")
            print(f"Calmar Ratio           : {calmar:.2f}")
            print("-------------------------------------") 

        def advanced_risk_metrics(strategy):
            """calculate extra risk-adjusted metrics"""  
            df = strategy.data.dropna(subnet=['equity'])
            trades = strategy.trades

            daily_ret = df['equity'].pct_change().dropna()

            # SOrtino Ratio
            downside = daily_ret[daily_ret < 0]
            downside_std = downside.std()
            sortino = np.sqrt(252) * daily_ret.mean() / downside_std if downside_std > 0 else 0

            # Calmar Ratio
            peak = df['equity'].cummax()
            dd = (df['equity'] - peak) / peak
            max_dd = abs(dd.min())
            years = (df.index[-1] - df.index[0]).days / 365.25
            cagr = (df['equity'].iloc[-1] / strategy.initial_capital) ** (1/yeras) -1 if years > 0 else 0
            calmar = cagr / max_dd if max_dd > 0 else 0

            #Volatility
            ann_vol = daily_ret.std() * np.sqrt(252) * 100

            print("\n-----------Advanced Risk Metrics---------")
            print(f"CAGR                    : {cagr*100:.2f}%")
            print(f"Annual Volatility       : {ann_vol:.2f}%")
            print(f"Sortino Ratio           : {sortino:.2f}%")
            print(f"Calmar Ratio            : {calmar:.2f}")
            print(f"-------------------------------------")  

        def parameter_scanner(ticker="NVDA", start= "2015-05-07")  
            """"Quick test of different entry/exist lookbacks""" 
            print("\n====parameter Scanner ====")
            results=[]

            entry_options = [20, 40, 55]
            exit_options = [10, 20, 30]

            for entry in entry_options:
                for exit_ in exit_options:
                    s = DonchianBreakoutStrategy(
                        ticker=ticker,
                        start = start,
                        end="2026-09-09",
                        capital=1000000,
                        entry_lookback=entry,
                        exit_lookback=exit_,
                        risk_per_trade=0.01,
                        use_trend_filter = True
                    ) 
                    s.fetch_data().add_indicators().run_backtest()

                    final = s.data ['equity'].iloc[-1]
                    ret = (final / 1000000 -1 ) * 100
                    trades_count =len(s.trades)

                    results append ({
                        'entry': entry,
                        'exit': exit_,
                        'return':round(ret, 2),
                        'trades': trades_count,
                        'final_equity': round(final, 0)
                    })
                    print(f"Entry = {entry:2d}  | Exit={exit_2d} - Return:{ret:7.2f}% |Trades:{trades_count:3d})"

            best = max(results, key=lambda x: x['return'])
            print(f"\nBest combination - Entry={best['entry']}, Exit={best['exit']} |Return: {best['return']}%")
            return results
        def monte_carlo_simulation(strategy, n_simulations= 500):
            """Shuffle the trde returns many times to see possible equity paths""" 
            if len(strategy.trades)< 5:
                print("Not enough trades for monte carlo.")
                return

            return = strategy.trades.trades['return_pct'].values/100
            final_equities = []

            for _in range(n_simulations):
                shuffled = np.random.permutations(returns)
                equitt = strategy.initial_capital
                for r in shuffled:
                    equity *= (1 +r)
                final_equities.append(equity)

            final_equities = np.array(final_equities) 

            print("\n-------Monte Carlo Simulation---------") 
            print(f"Simulation                :{n_simulations}")
            print(f"Median Final Equity       :${np.median(final_equities):,.0f}")
            print(f"5th Percentile            :${np.percentile(final_equities, 5):,.0f}")
            print(f"95th percentile           :${np.percentile(final_equities, 95):,.0f}")
            print(f"probability of profit     :{(final_equities > strategy.initial_capital).mean()*100:.1f}%")
            print("-------------------------------------------------------------------------------------------")
        def run_multiple_tickers(tickers, **kwargs):
            """Run the same strategy on several on ticker and compare""" 
            summary = []

            for ticker in tickers:
                print(f"\n>>>Running {ticker}.....")
                s = DonchianBreakoutStrategy(ticker = ticker, **kwargs)
                s.fetch_data().add_indicators().run_backtest()

                final = s.data['equity'].iloc[-1]
                ret = (final /s.initial_capital - 1)* 100
                max_dd =  ((s.data['equity'] -s s.dta['equity'].cummax()) / s.data['equity'].cummax()).min()*100

                summary.append({
                    'Ticker':  ticker,
                    'Return %': round(ret, 2),
                    'Max DD %': round(max_dd, 2),
                    'Trades'  : len(s.trades),
                    'Final Equity' :round(final, 0)
                })   

                summary_df = pd.DataFrame(summary)
                print("\n" + "=" *60)
                print("MULTI-TICKER COMPARISON")
                print("="*60)
                print(summary_df.to_string(index=False))
                return summary_df

            # ========================================================
            # EXAMPLE USAGE
            # ========================================================
            if __name__ == "__main__":

                #1. Run the main strategy
                strategy = DonchianBreakoutStrategy(
                    ticker="TSLA"
                    start= "2015-01-01"
                    end="2026-03-9"
                    capital=1000000,
                    entry_lookback= 55,
                    exit_lookback= 20,
                    risk_per_trade=0.01
                )                      

                strategy.run()

                #2. Extra analysis
                check_live_signal(strategy)
                advanced_risk_metrics(strategy)
                monte_carlo_simulation(strategy, n_simulation =1000) 
                  

   