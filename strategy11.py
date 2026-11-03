import yfinance as yf
import streamlit as st
import pandas as pd
import numpy as np
import time
from datettime import datetime
import requests
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title = "NSE Live Monitor",
    page_icon = "📊",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

# ======================================================================================================================
# STOCK LIST
# ======================================================================================================================
STOCKS = {
    "SCOM.NR"     : "Safaricom",
    "EQTY.NR"     : "Equity Group",
    "KCB.NR"      : "KCB Group",
    "COOP.NR"     : "Co-operative Bank",
    "EABL.NR"     : "EABL",
    "BAT.NR"      : "BAT Kenya",
    "NCBA.NR"     : "NCBA",
    "ABSA.NR"     : "Absa Bank",
    "SBIC.NR"     : "Stanbic",
    "IMH.NR"      : "I&M Holdings",
    "DTK.NR"      : "Diamond Trust",
    "SCBK.NR"     : "Standard Chartered"
}

# ==============================================================================================================
# TELEGRAM FUNCTION
# ===============================================================================================================
def send_telegram(msg, token, chat_id):
    try:
        url = f"https://api.telegram.org/bot{token}/ sendMessage"
        requests.post(url, data={"Chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=8)
        return True
    except:
        return False

# ===================================================================================================================
# SCAN FUNCTION
# ====================================================================================================================
def scan_stock(ticker, name, price_limit=1.2, vol_limit=2.0):
    try:
        df = yf.download(ticker, period="2d", interval="1m", progress="False", auto_adjust=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < 20:
            return None

        df = df.dropna()
        current = df.iloc[-1]
        price = float(current["Close"])
        volume = float(current["Volume"])

        # Short-term change ( last 8-10min)
        lookback = df.tail(12)
        change = ((price - lookback["Close"].iloc[0]) / lookback["Close"].iloc[0]) * 100


        #  Volume Ratio
        avg_vol = df["Volume"].tail(40).mean()
        vol_ratio = volume / avg_vol if avg_vol > 0 else 1

        # Anomaly rules
        reasons = []
        score = 0

        if abs(change) >= price limit:
            score += 2
            direction = "UP" if change > 0 else"DOWN"
            reasons.append(f"Price {direction} {abs(change):.2f}%")

        if vol_ratio >= vol_limit:
            score += 1
            reasons.append(f"Volume x {vol_ratio:.1f}")

        is_alert = score >= 2
        return {
            "ticker"     : ticker,
            "name"       : name,
            "price"      : round(price, 2),
            "change"     : round(change, 2),
            "vol_ratio"  : round(vol_ratio, 2),
            "is_alert"   : is_alert,
            "reasons"    : reasons,
            "score"      : score,
            "time"       : datetime.now().strftime("%H:%M:%S") 
        }
    except:
        return None

# =================================================================================================
# SIDEBAR
# ==================================================================================================
st.sidebar.title("NSE live Monitor")

st.sidebar.markdown("### Alerts Settings")
price_limit =st.sidebar.slider("Price move %", 0.8, 3.0, 1.3, 0.1)
vol_limit = st.sidebar.slinder("Volume spike", 1.5, 4.0, 2.2, 0.1)
scan_every = st.sidebar.slider("Scan Interval (sec)", 15, 60, 25)

st.sidebar.markdown("---")
use_telegram = st.sidebar.checkbox("Telegram Alerts")
bot_token = st.sidebar.text_input("Bot Token", type="password") if use_telegram else None
chat_id = st.sidebar.text_input("Chat ID") if use_telegram else None

play_sound = st.sidebar.checkbox("Browser sound Alert", value=True)
auto = st.sidebar.checkbox("Auto monitoring", value=True)

# ==================================================================================================
# SESSION STATE
# ===================================================================================================
if "alert_history" not in st.session_state:
    st.session_state.alert_history = []
if "last_time" not in st.session_state:
    st.session_state.last_time = "Not yet"

# ==================================================================================================
# MAIN
# =================================================================================================
st.title("NSE live Anomaly Monitor")
st.caption("REal-time monitoring of liquid kenyan stocks")

status_col1, status_col2, status_col3 = st.columns(3)
status_col1.metric ("monitoring", f"{len(STOCKS)} stocks")
status_col2.metric ("Last Scan", st.session_state.last_time)
status_col3.metric ("Alerts Today", len(st.session_state.alert_history))

placeholder = st.empty()

def do_scan():
    results = []
    alerts_found = []

    for ticker, name in STOCKS.item():
        data = scanstock(ticker, name, price_limit, vol_limit)
        if data:
            results.append(data)
            if data["is_alert"]:
                alerts_found.append(data)

                # Save alert
                alert_msg = f"{data['name']}: {','.join(data['reasons'])} | {data['change']:+.2f}%"
                st.session_state.alert_history = st.session_state.alert_history[:25]

                # Telegram
                if use_telegram and bot_token and chat_id:
                    tg_msg = f"<b>{data['name']}</b>\nPrice: {data['price']}\nChange: {data['change']:+.2f}%\n{','.join(data['reasons'])}"
                    send_telegram(tg_msg, bot_token, chat_id)

    
    st.session_state.last_time = datetime.now().strftime("%H:%M:%S")
    return results, alerts_found

# Manual button
if st.button("Scan Now", use_container_width= False):
    with st.spinner("Scanning......."):
        results, alerts = do_scan()

# Auto mode
if auto:
    results, alerts = do_scan()

    with placeholder.container():
        # Alert banner
        if alerts:
            st.error(f"{len(alarts)} ANOMALY DETECTED")
            for a in alerts:
                st.warnings(f"**{a['name']}** → {','.join(a['reasons'])} | price: **({a['change']:+.2f}%)")

            # Sound alert using HTML
            if play_sound:
                st.markdown(
                    """
                    <audio autoplay>
                    <source src = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg type="audio/ogg">
                    </audio>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.success("No major anomalies right now")

                # Live table
                if results:
                    df = pd.DataFrame(results)
                    df = df[["name", "price", "change", "vol_ratio", "is_alert", "time"]]
                    df.columns = ["Stock", "price (KES)", "Change %", "Vol Ratio", "Alert", "Time"]
                    df = df.sort_values("Change %", ascending=False)

                    st.dataframe(
                        df.style.applymap(
                            lamda x: "background-color: #ffccc" if x == True else "",
                            subset=["Alert"]
                        ),
                        use_container_width = True,
                        height= 400
                    )
            # Alert history
            st.subheader("Recent Alerts")
            if st.session_state.alert_history:
                for item in st.session_state.alert_history[:12]:
                    st.text(f"{item['time']} → {item['msg']}")
            else:
                st.info("No alerts yet. System is watching.....")

            time.sleep(scan_every)
            st.rerun()
        else: 
            st.info("Enable **Auto Monitoring** in the sidebar to start live scanning")
            