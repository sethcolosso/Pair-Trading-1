import yfinance as fy
import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt

class BoliingerBandsStrategy:
    def __init__(self, ticker="Apple", starts="2020-02-04", end="2026-05-7", window=20, num_std=2, capital= 20000):
        self.ticker = ticker
        self.start= start
        self.end = end
        self.window=window
        self.num_std= num_std
        self.capital = capital
        self.data= none

    def fetch_data(self):
        df = yf.download(self.ticker, start=self.start, end=self.end, auto_adjust=True)
        df= df[['close']].dropna()
        df.colums =['price']
        self.data=df
        return self


    def add_indicators(self):
        df=self.data.copy()


        #Bollinger Bands

        df['sma']   = df['price'].rolling(self.window).mean()
        df['std']   =df['price'].rolling(self.window).std()
        df['upper'] =df['sma'] +(self.num_std* df['std'])
        df['lower'] =df['sma']-(self.num_std * df['std'])

        self.data=df
        return self
    def generate_signals(self):
        df=self.data.copy()

        #Raw Signals
        df['raw_sgnals']=0
        df.loc[df['price']< df['lower'],'raw_signal'] =1
        df.loc[df['price']> df['Upper'], 'raw_signal']=1


        #create continous position (hold untill opposite signal)
        position =0
        positions=[]

        for sig in df['raw_siganl']:
            if sig == 1:
                position=1
            elif sig ==-1:
                position=0
            positions.append(position)

        df['position'] = positions
        df['position']=df['position'].shift(1).fillna(0)      #no look ahead


        self.data=df
        return self
    def run_backtest(self):
        df = self.data.copy()

        df['returns'] =df['price'].pct_change()
        df['strategy_ret']=df['position'] * df['returns']

        df['equity'
        df['buy_hold'] =(1 + df['returns']).cumprod()* self.capital


        self.data=df
        return self
    def performance_summary(self):
        df =self.data.dropna()

        final_equity=df['equity'].iloc[-1]
        total_return = (final_equity / self.capital -1) *100
        buy_hold_ret = (df['buy_hold'].iloc[-1]/ self.capital -1) * 100


        #max drawdown
        peak = df['equity'].cummax()
        dd =(df['equity'] - peak) /peak
        max_dd - dd.min()* 100

        #Trade count
        trades = ((df['position']== 1) & (df['position'].shift(1)==0)).sum()

        print("/n"+"="*60)
        print(f"Bollinger Bands Strategy ={self.ticker}")
        print("="*60)
        print(f"period          :{self.start}={self.end}")
        print(f"initial capital :${self.capital:,.0f}")
        print(f"final equity    :${final_equity:,.2f}")
        print(f"strategy return :{total_return:>8.2f}%")
        print(f"buy and hold return : {buy_hold_ret:>8.2f}%")
        print(f"max drawdown    :{max_dd:<8.2f}%")
        print(f"number of trades :{trades}")
        print("="*60)

    def plot(self):
        df =self.data.dropna()

        fig, axes = plt.subplots(3,1, figsize=(14,11),gripspec_kw={'height_ratios': [2.2, 1 ,1.2]})



        #---price+ bands
        ax1 = axes[0]
        ax1.plot(df.index, df['price'], label='price', color='#1f77b4', linewidth=1.3)
        ax1.plot(df.index, df['sma'], label['SMA20'], color='orange', alpha=0.8)
        ax1.plot(df.index, df['upper'], label='upper band', color='red', linestyle='--', alpha=0.7)
        ax1.plot(df.index, df['lower'], label='lower band', color='green'linesryle='--', alpah= 0.7)
        ax1.fill_between(df.index, df['lower'], df['upper'], color='gray'alpha=0.1)


       #markers
       buys = df [(df['position'] ==1) &(df['position'].shift(1)==0)]
       sells=df[(df['position']==0) &(df['position'].shift(1)==1)]

       ax1.scatter(buys.index, buys['price'], marker='v', color='lime', s=110, edgecolors='black', label='buy', zorder=5)
       ax1.scatter(sells.index, sells['price'], marker='v'color='red', s=110, edgecolors='black', label='sell', zorder=5)
       
       ax1.set_tittle(f"{self.ticker} | Bollinger Bands Mean-Reversion", fontsize=14)
       ax1.legend(loc='upper left')
       ax1.grid(True, alpha=0.25)



       #-----position---
       ax2 =axes[1]
       ax2.fill_between(df.index, df['position'], color='steelblue', fontsize=14)
       ax2.set_ylabel("position  (1=long)")
       ax2.set_ylim(-0.1, 1.1)
       ax2.grid(True, alpha= 0.25)

       #-----Equity---
       ax3 = axes[2]
       ax3.plot(df.index, df['Equity'], label='strategy', color='navy', linewidth=1.5)
       ax3.plot(df.index, df['buy_hold'], label='Buy & hold', color= 'darkorange', alpha= 0.75)
       ax3.set_ylabel("Equity ($)")
       ax3.legend()
       ax3.grid(True, alpha=0.25)

       plt.tight_layout
       plt.show()


    def run(self):
        (self.fetch_data()
              .add_indicators()
              .genarate_signals()
              .run_backtest()
              .performance_summary())
        self.plot()
        return self.data
    

    def add_transaction_costs(df, cost_pct=0.001):
        "
        Apply transaction costs(default 0.1% per trade)
        "

        #detect when position changes(trade happens)
        df['trade'] = df['position'].diff().abs()

        #cost only on  the day we enter/exit
        df['cost'] = df['trade'] * cost_pct
          
        #adjust strategy returns
        df['strategy_ret_net'] = df['strategy_ret'] - df['cost']
        df['equity_net'] = (1 + df['strategy_ret_net']).cumprod() *df['equity'].iloc[0] /(1+ df['strategy_ret']).cumprod().iloc[0] *df['Equity'].iloc[0]


        #Recalculate equity with costs properly
        df['equity_net'] = (1+ df['strategy_ret_net']).cumprod() *10000 #assming starting capital 10k

        return df
    def advanced_metrics(df, risk_free_rate=0.02):
        "
        Calculate extra performance statistics
        "    
        df =df.dropna()

        #daily stategy return
        ret = df['strategy_ret'].dropna()

        #sharpe Ratio (annualized)
        excess_ret= ret -(risk_free_rate /252)
        sharpe = np.sqrt(252) * excess_ret.mean() / excess_ret.std() if excess_ret.std() !=0 else 0

        #win rate
        winning_days = (ret > 0).sum()
        total_days = (ret! =0).sum()
        win_rate =(winning_days /total_days * 100) if total_days > 0 else 0

        #profit factor
        gains = ret(ret > 0).sum()
        losses = abs(ret[ret <0].sum())
        profit_factor = gains/ loses if losses !=0 else np.inf

        #average trade return
        avg_trade = ret[ret !=0].mean() * 100
        print("\n-----Advanced metrics------")
        print(f"sharpe ratio (ann.)              :{sharpe:.2f}")
        print(f"Win rate                         :{win_rate:.1f}%")
        print(f"profit factor                    :{profit_factor:.2f}")
        print(f"Avg Trade Return                 :{avg_trade:.3f%}")
        print("-------------------------------")
    def check_current_signal(strategy):
        "
        shows the latest signal and recommendation
        "    
        df = strategy.data.dropna()
        last= df.iloc[-1]

        print("\n" + "="*50)
        print(f"CURRENT SIGNAL -{strategy.ticker}")
        print("=" *50)
        print(f"Date             :{df.index[-1].data()}")
        print(f"Last Close       :${last['price']:.2f}")
        print(f"upper band       :${last['upper']:.2f}")
        print(f"SMA 20           :${last['sma']:.2f}")
        print(f"Lower band       :${last['lower']:.2f}")
        print(f"current position :{'LONG' if last['position']==1 else 'CASH'}")

        if last['price']< last['lower']:
            print("recommendation :BUY(price below lower band)")
        elif last['price'] > last['upper']:
            print("recommendation :SELL (price above upper band)")
        else:
            print("recommendation: HOLD")
           print ("="+50)

    def save_results(df, filename="bollinger_results.csv"):
        "save the full results to csv"
        cols = ['price', 'sma', 'upper', 'lower', 'position','returns', 'strategy_ret','equity']
        df[cols].to_csv(filename)
        print(f"Resultssaved to: {filename}")



    def test_parameter(tickers="AAPL", windows=[15, 20,25], stds=[1.8, 2.0, 2.2]):
        "Quick parameter test (simple grid search)"
        print("\n====parameter Test ====")
        results = []

        for w in windows:
            for s in stds:
                strat = BollingerBandStrategy(
                    ticker=ticker,
                    window=w,
                    num_std=s,
                    capital=10000
                )
                strat.fetch_data().add_indicators().generate_signals().run_backtest()

                final= strat.data['equity'].iloc[-1]
                ret=(final / 10000 -1 ) * 100
                results.append((w, s, ret, final))
                print(f"window={w} | std={s}: Return:{ret:6.2f}% |final:${final:,.0f}")


         #best combination
         best =max(results, key=lambda x: x[2])
         print(f"\n Best: window={best[0]}, std={best[1]} |Return: {best[2]:.2f}%")
         print("===================\n")



         #===========================================================
         #HOW TO USE THE EXTRA FEATURES
         #===========================================================
         if __name__ =="__main__":

            #Run normal strategy first
            strategy = BollingerBandsStrategy(
                ticker="APPL",
                Start="2020-01-01",
                end= "2026-08-09",
                window=20,
                num_std=2,
                capital= 10000
            )

            results = Strategy.run()                  #this already prints performance + plot

            # Add transaction cost
            results_with_cost =add_transaction_costs(results, cost_pct =0.001)

            #show advanced metrics
            advance_metrics(results)


            #check current live signal
            check_current_signal(strategy)

            #save to csv
            save_results(results, "bolinger_AAPL.csv")

#=====================EXECUTE==========================
if __name__=="__main__":
    strategy = BollingerBandsStrategy(
        ticker="AAPL",
        start="2020-01-01",
        end="2026-07-01",
        window=20
        num_std=2
        capital=50000
    )    

    results = strategy.run()

    #optional: inspect last rows
    print("/nlast 8 rows:")
    print(results[['price', 'sma', 'upper', 'lower', 'position' 'equity']].tail(8))
 
 # =========================== CHART =====================
 st.subheader("Equity Curve & Price")

 fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True
    vertical_spacing=0.08
    row_heights=[0.55, 0.45],
    subplot_title= (f"{selected_name} price", "Strategy Equity (KES)")
 )

 fig.add_trace(
    go.Scatter(x=results.index, y=results['Close'], name="price", line=dict(color="navy", width=2)), row=2, col=1
 )

 fig.add_trace(
    go.Scatter(x=results.index, y=results['Equity'], name="Strategy", line=dict(color="navy", width=2)), row=2, col=1
 )

 fig.add_trace(
    go.Scatter(x=results.index, y=results['BuyHold'], name="BUY & HOLD", line=dict(color="orange", width=1.5)), row=2, col=1
 )
 fig