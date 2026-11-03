import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datatime import datetime

 class MACDTrendstrategy:
    def __init__(
        self,
        ticker="AAPL",
        start="2020-01-01",
        end="2026-07-08",
        capital= 20000,
        stop_loss_pct=0.06,
        risk_per_trade=0.01,
        transaction_cost=0.001,
        trailing_stop_pct=0.08,
        fast=12,
        slow=26,
        siganal=9

    ):

        self.ticker=ticker
        self.start=start
        self.end=end
        self.capital=capital
        self.risk_per_trade=risk_per_trade
        self.stop_loss_pct=nstop_loss_pct
        self.trailling_stop_pct= trailing_stop_pct
        self.transaction_cost= transaction_cost
        self.fast=fast
        self.slow=slow
        self.signal=signal

        self.data=None
        self.trades=[]

    def fetch_data(self):
        print(f"Downloading data for {self.ticker}.....")
        df=yf.download(self.ticker, start=self.start, end=self.end, auto_adjust=True)
        df=df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df.columns =['open', 'high', 'low', 'close','volume']
        self.data=df
        return self

    def add_indicators(self):
        df=self.data.copy()

        #MACD
        ema_fast= df['close'].ewm(span=self.fast, adjust=false).mean()
        ema_slow=df['close'].ewm(span=self.slow, adjust=false).mean()
        df['macd'] = ema_fast -ema_slow
        df['macd_signal']=df['macd'].ewm(span=self.signal, adjust=False).mean()
        df['macd_hist'] =df['macd'] -df['macd_signal']


        #Trend filter
        df['sma_200'] =df['close'].rolling(200).mean()

        #ATR for volatility (optional useful later)
        df['tr'] = np.maximum(
            df['high'] -df['low'], np.maximum(
                abs(df['high'] - df["close"].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )     
        df['atr'] =df['tr'].rolling(14).mean()

        self.data=df
        return self
    def generate_signals(self):
        df=self.data.copy()


        #MACD crossover
        df['macd_cross_up'] =(df['macd'] > df['macd_signal']) &(df['macd'].shift(1) <= df['macd_signal'].shift(1)) 
        df['macd_cross_down'] =(df['macd'] < df['macd_signal']) &(df['macd'].shift(1) >=df['macd_signal'].shift(1))

        #trend filter: only long when price > 200 SMA 
        df['uptrend'] =df['close'] >df['sma_200']

        #Final Signal
        df['signal']=0
        df.loc[df['macd_cross_up'] &df['uptrend'], 'signal']=1
        df.loc[df['macd_cross_down'], 'signal'] =-1

        self.data = df
        return self
    def backtest(self):
        df=self.data.copy()

        cash =self.capital
        position=0
        entry_price=0
        stop_price=0
        trailing_high=0
        equity_curve=[]
        trade_log=[]

        for i in range(len(df)):
            row=df.iloc[i]
            date=df.index[i]
            price= row['close']


            #=========EXIT LOGIC=====
            if position > 0:
                #update trailing high
                trailing_high =max(trailing_high, price)
                trailing_stop =trailing_high * (1 - self.trailing_stop_pct)  

                #stop loss or trailing stop hit
                if price <= stop_price or price <= trailing_stop:
                    #Sell
                    proceeds = position * price *(1 - self.transaction_cost)
                    cash += proceeds
                    pnl = proceeds - (position * entry_price)
                    trade_log.append({
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price':entry_price,
                        'exit_price': price,
                        'shares':position,
                        'pnl':pnl,
                        'return_pct': (price/ entry_price -1) *100,
                        'reason': 'Stop/ Trailing'
                    })
                    position = 0


                    #MACD exit signal
                    elif row ['signal'] == -1:
                        proceeds = position * price(1 - self.transaction_cost)
                        cash += proceeds
                        pnl = proceeds - (position * entry_price )
                        trade_log.append({
                            'entry_date': entry_date,
                            'exit_date': date,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'shares':position,
                            'pnl': pnl,
                            'return_pct': (price/ entry_price -1) *100,
                            'reason':'MACD Cross Down'
                        })
                        position = 0
                        ===========Entry logic=======
                        if position == 0 and row ['signal'] ==1:
                            #position sizing based on risk
                            risk_amount =cash * self.risk_per_trade
                            stop_distance =price * self.stop_loss_pct
                            shares = int(risk_amount / stop_distance)

                            if shares > 0 and cash > shares * price:
                                cost = shares*price*(1+ self,transaction_cost)
                                if cost <= cash:
                                    cash-= cost
                                    position=shares
                                    entry_price =price
                                    entry_date = date
                                    stop_lprice =price * (1 - self.stop_loss_pct)
                                    trailing_high = price

                         #Record equity
                         current_equity = cash +(position * price)
                         equity_curve.append(current_equity)

                    df['equity'] = equity_curve
                    df['buy_hold'] = (1 + df['close'].pct_change()).cumprod() * self.capital

                    self.data =df
                    self.trades = pd.DataFrame(trade_log)
                    return self

                def performance_report(self):
                     df + self.data.dropna()
                     trades = self.trades

                     final_equity =df['equity'].iloc[-1]
                     total_return = (final_equity / self.capital -1) * 100
                     buy_hold_return =(df['buy_hold'].iloc[-1] / self.capital -1) * 100

                     #Drawdown
                     peak = df['equity'].iloc[-1]
                     dd = (df['equity'] - peak) / peak
                     max_dd =dd.min() * 100

                     #Trade statistics
                    if len(trades) > 0:
                        win_trades = trade[trades['pnl'] <= 0]
                        loss_trade = trade[trades['pnl'] <= 0]


                        win_rate = len(win_trades)  /len (trades) * 100
                        avg_win = win_trade['return_pct']>mean() if len(win_trades) > 0 else 0 
                        profit _factor =abs(win_trades['pnl'].sum()/ loss_trade['pnl'].sum()) if len(loss_trade) > 0 and loss_trade['pnl'].sum() ! else np.inf
        
                    else: 
                        win_rate = avg_win = avg_loss = profit_factor = 0

                        #sharpe
                        daily_ret = df ['equity'].pct_change().dropna()
                        sharpe = np.sqrt(252) * daily_ret.mean() /daily_ret.std() if daily_ret.std() !=0 else 0


                        print("\n" + "=" *65)
                        print(f"MACD + 200 SMA TREND STRATEGY :{self.ticker}")
                        print("=" *65)
                        print(f"period               : {self.start}")
                        print(f"Intial Capital       :${self.capital:,.0f}")
                        print(f"Final Equity         :${final_equity:,.2f}")
                        print(f"total Return         :{total_return:>8.2f}%")
                        print(f"Buy & Hold return    :{buy_hold_return:>8.2f}%")
                        print(f"max drawdown         :{max_dd:>8.2f}%")
                        print(f"sharpe ratio         :{sharpe:>8.2f}")
                        print(f"-"*65)
                        print(f"Total Trades         :{len(trades)}")
                        print(f"Win rate             :{win_rate:>8.1f}%")
                        print(f"Average Win          :{avg_win:>8.2f}%")
                        print(f"Average loss         :{avg_loss:8.2f}%")
                        print (f"Profit Factor       :{profit_factor:8.2f}")
                        print("="*65)

                        if len(trades) > 0:
                            print("\n Last 5 trades:")
                            print(trades[['entry_date', 'exit_date', 'entry_price', 'exit_price', 'return_pct', 'reason']].tail().to_string(index=False))

                    def plot(self):
                        df = self.data.dropna()

                        fig,axes = plt.subplots(4,1, figsize=(15, 13), gridspec_kw ={'height_ratios':[2.2, 1, 1, 1.3]})

                        #price + SMA 200 +trades
                        ax1 = axes[0]
                        ax1.plot(df.index, df['close'],label='Close', color='black', alpha=0.8)
                        ax1.plot(df.index, df['sma_200'], label='SMA 200', color='orange', alpha=0.8)


                        if len(self.trades) > 0:
                            for _, trade in self.trades.iterrows():
                                ax1.scatter(t['entry_date'], t['entry_price'], color='lime', marker='^', s=90, zorder= 5)
                                ax1.scatter(t['exit_date'], t['exit_price'], color='red', marker='v', s=90, zorder=5)

                        ax1.set_title(f"{self.ticker} - MACD + 200 SMA TrendStrategy", fontsize=14)
                        ax1.legend(loc='upper left')
                        ax1.grid(True, alpha=0.25)

                        #MACD
                        ax2 = axes[1]
                        ax2.plot(df.index, df['macd'], label ='MACD', cplor='blue')
                        ax2.plot(df.index, df['macd_signal'], label ='signal', color='red', alpha=0.8)
                        ax2.bar(df.index, df['macd_hist'], label='Histogram', color='gray',alpha=0.4)
                        ax2.axhline(0, color='black', linewidth=0.7)
                        ax2.legend(loc='upper left')
                        ax2.grid(True, alpha=0.25)

                        #position/ Exposure
                        ax3 = axes[2]
                        position_series =(df['equity'] - df['equity'].shift(1).fillna(self.capital))
                        ax3.fill_between(df.index, df['equity'] > df['equity'].shift(1), alpha= 0.3)
                        ax3.set_ylabel("Equity Chnages")
                        ax3.grid(True, alpha=0.25)

                        #Equity curve
                        ax4 = axes[3]
                        ax4.plot(df.index, df['equity'], label='strategy', color='navy', linewidth=1.6)
                        ax4.plot(df.index, df['buy_hold'], label='buy & hold', color = 'darkorange', alpha=0.75)
                        ax4.set_ylabel("portfolio value ($)")
                        ax4.legend()
                        ax4.grid(True, alpha=0.25)

                        plt.tight_layout()
                        plt.show()
                    def run(self):
                        (self.fetch_data()
                             .add_indicators()
                             .generate_signals()
                             .backtest()
                             .performance_report())
                        self.plot()
                        return self

#=======================================================================
#RUNNING STRATEGY
#=======================================================================

 if __name__ =="__main__":
    strategy = MACDTrendStrategy(
        ticker ="AAPL",
        start="2018-01-01",
        end="2025-07-06",
        capital =20000,
        risk_per_trade=0.015,
        stop_loss_pct=0.07,
        trailing_stop_pct=0.10,
        transaction_cost=0.001
    )

    strategy.run()

    #Optional:save trade log
    if len(Strategy.trades) >0:
        strategy.trades.to_csv("macd_trades.csv", index=False)
        print("\nTrade log saved - macd_ trades.csv")
        