import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


#=================congig
TICKER ="AAPL"
START_DATE ="2020-01-01"
END_DATE="2026-03-05"
SHORT_WINDOW=20             #short moving average
LONG_WINDOW=50              #long moving average
INITIAL_CAPITAL=10000       #starting cash

def get_data(ticker,start,end):
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)
    data = data[['close']].copy()
    data.columns =['close']
    return data
 def generate_signals(data, short_window, long_window):
    data = data.copy()

    #calculate moving averages
    data['SMA_Short'] = data ['Close'].rolling(window=short_window).mean()
    data['SMA_Long'] = data['Close'].rolling(window=long_window).mean()

    #generate signals 
    data['Signal'] = 0
    data.loc[data['SMA_Short'] >data['SMA_Long'], 'Signal'] = 1   #buy/hold long
    data.loc[dta['SMA_Short'] < data['SMA_Long'], 'Signal'] = 0   #sell/stay in cash

    #position: 1=long, 0 =cash
    data['position'] = data['Signal'].shift(1)         #use previous day's signal to avaoid look-ahead bias
    data['position'] = data['position'].fillna(0)

    return data
def backtest(data, initial_capital=1000):
    data = data.copy()

    #Daily returns of the asset
    data['Returns'] = data['Close'].pct_change()

    #Strategy returns (only when we are long)
    data['Strategy_Returns'] = data['Position'] *data['Returns']

    #Equity curve
    data['Equity'] = (1 + data['Strategy_Returns']).cumprod() * initial_capital
    data['Buy_hold_equity'] = 1 = data['Position'].cumprod() * initial_capital

    return data
def plot_results(data. ticker):
    fig, (ax1, ax2) = plt.subplots(2 ,1, figsize=(14, 10), gridspec_kw={'height_ratio':[2,1]} )


    #price + moving average
    ax1.plot(data.index, data['close'], label='close price', alpha=0.6)
    ax1.plot(data.index, data['SMA_Short'], label=f'SMA {SHORT_WINDOW}', alpha=0.8)
    ax1.plot(data.index, data['SMA_Long'], label=f'SMA{LONG_WINDOW}', alpha=0.8)


    # buy  / sell markets
    buy_signals = data[(data['position']==1) & (data['position'].shift(1)==0)]
    sell_signals =data[(data['position']==0)& (data['position'].shift(1)==1)]

    ax1.scatter(buy_signals.index, buy_signals['Close'], marker='*', color='green', s=100, label= 'buy', zorder=5)
    ax1.scatter(sell_signals.index, sell_signals['Close'], marker='*', color='red', s=100, label='sell', zorder=5)

    ax1.set_tittle(f'{ticker} - moving average crossover strategy')
    ax1.set_ylabel('price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    #Equity curve
    ax2.plot(data.index, data['Equity'], label='strategy Equity', color='blue')
    ax2.plot(data.index,data['buy_hold_equity'], label='buy and hold' , color='orange', alpha=0.7)
    ax2.set_tittle('Equity curve')
    ax2.set_ylabel('portfolio value ($)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
def print_performance(data, initial_capital):
    total_return= (data['Equity'].iloc[-1]/ initial_capital-1) * 100
    buy_hold_return=(data['buy_hold_equity'].iloc[-1] /initial_capital -1) * 100

    #maximum Dramdown
    rolling_max = data['Equity'].cummax()
    drawdown = (data['Equity'] - rolling_max) /rolling_max
    max_drawdown = drawdown.min() *100

    print("=" * 50)
    print(f"strategy performance ({TICKER})")
    print("=" * 50)
    print(f"initial capital         : ${initial-capital:,.2f}")      
    print(f"Final Equity            : ${data['Equity'].iloc[-1]:,.2f}")
    print(f"Totoal Return           : {total_return:.2f}%")
    print(f"buy & hold return       : {buy_hold_return:.2f}%")
    print(f"Max Drawdown            : {max_drawdown:.2f}%")
    print("=" * 50)
    

    #=============RUN=========
    if __name__=="__main__":
        #1. Get data
        df = get _data(TICKER,START_DATE, END_DATE)

        #2. erate Signals
        df =generate_signals(df,SHORT_WINDOW,LONG_WINDOW)

        #3. ktest
        df _backtest(df, INITIAL_CAPITAL)

        #4. Results
        print_performance(df, INITIAL_CAPITAL)
        plot_results(df, TICKER)

        #optional: see last few rows
        print("\nlasst 10 rows of signals:")
        print(df[['close', 'SMA_short', 'SMA_long','position', 'equity']].tail(10))
        