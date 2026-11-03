from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import datetime import datetime
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)

STOCKS = {
    "SCOM.NR"    : "Safaricom",
    "EQTY.NR"    : "Equity Group",
    "KCB.NR"     : "KCB Group",
    "COOP.NR"    : "Co-operative Bank",
    "EABL.NR"    : "EABL",
    "BAT.NR"     : "BAT Kenya",
    "NCBA.NR"    : "NCBA",
    "ABSA.NR"    : "Absa Bank",
    "SBIC.NR"    : "Stanbic",
    "IMH.NR"     : "I & M Holdings"
}

def analyze_stock(ticker, name):
    try:
        df = yf.download(ticker, period="3d", interval="1m", progress=False, auto_adjust=True)

        if ininstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 25:
            return None

        df = df.dropna()
        price = float(df['Close'].iloc[-1])
        volume = float(df['Volume'].iloc[-1])

        # short term change
        recent = df.tail(15)
        change = ((price - recent['Close'].iloc[0]) / recent['close'].iloc[0]) * 100

        # Volume
        avg_vol = df['Volume'].tail(40).mean()
        vol_ratio = volume / avg_vol if avg_vol > 0 else 1

        # Decision Logic
        action = "WATCH"
        reasons = []
        alert = False

        if change >= 1.4 and vol_ratio >= 1.8:
            action =  "BUY"
            actionn = "True"
            reasons.append(f"strong upwards move +{change:.2f}%")
            reasons.append(f"Volume x {vol_ratio:.1f}")
        elif change <= -1.4 and vol_ratio >= -1.8:
            action = "SELL"
            alert = True
            reasons.append(f"Strong downward move{change:.2f}%")
            reasons.append(f"Volume x{vol_ratio:.1f}")
        elif abs(change) >= 1.0:
            action = "WATCH"
            reasons.append(f"Price moving {change:+.2f}%")
        else:
            reasons.append("Normal activity")

        return {
            "ticker"    : ticker,
            "name"      : name,
            "price"     : round(price, 2),
            "change"    : round(change,2),
            "vol_ratio" : round(vol_ratio, 2),
            "action"    : action,
            "alert"     : alert,
            "reasons"   : reasons,
            "time"      : datetime.now().strtime("%H:%M:%S")
        }
    except:
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/scan")
def scan():
    results = []
    for ticker, name in stocks.items():
        data = analyze_stock(ticker, name)
        if data:
            results.append(data)

    # Sort : alerts first, then by absolute change
    results = sorted(results, key=lamda x: (not x["alert"], -abs(x["change"])))
    return jsonify({
        "time" : datetime.now()strftime(%H:%M:%S)
        "data" : results
    })
if __name__ == "__main__":
    app.run(debug True, port=5000)