
import streamlit as st
import pandas as pd
import yfinance as yf
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# === Must be FIRST Streamlit command ===
st.set_page_config(page_title="TWSE Sector Rotation Dashboard", layout="wide")

# === Version Indicator ===
APP_VERSION = "v1.2.0 - CIO Commentary Upgrade"
st.sidebar.markdown(f"**📄 App Version:** `{APP_VERSION}`")

# --- Sidebar ---
st.sidebar.title("⚙️ Settings")
uploaded_file = st.sidebar.file_uploader("Upload your watchlist.csv", type="csv")

if uploaded_file:
    watchlist = pd.read_csv(uploaded_file)['Ticker'].dropna().tolist()
else:
    st.sidebar.warning("Please upload a watchlist.csv to proceed.")
    st.stop()

start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=365*10))
end_date = st.sidebar.date_input("End Date", datetime.today())

# --- Data Fetching ---
st.title("📊 TWSE Sector Rotation Intelligence Dashboard")
st.info("Fetching live data...")

@st.cache_data(show_spinner=False)
def fetch_data(tickers, start, end):
    records = []
    sectors = {}
    with requests_cache.CachedSession():
        for tkr in tickers:
            try:
                tk = yf.Ticker(tkr)
                hist = tk.history(start=start, end=end, interval='1mo')[['Volume']].reset_index()
                hist['Ticker'] = tkr
                records.append(hist)
                sectors[tkr] = tk.info.get('industry', 'Unknown')
            except:
                continue
    df = pd.concat(records, ignore_index=True)
    df['Sector'] = df['Ticker'].map(sectors)
    df['Date'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
    agg = df.groupby(['Date','Sector'])['Volume'].sum().reset_index()
    return agg

agg_df = fetch_data(watchlist, start_date, end_date)

# --- Charts ---
st.subheader("📈 Sector Volume Trends")
pivot = agg_df.pivot(index='Date', columns='Sector', values='Volume').fillna(0)
fig, ax = plt.subplots(figsize=(12,6))
pivot.plot.area(ax=ax)
st.pyplot(fig)

st.subheader("🔥 Sector Volume Intensity Heatmap")
pivot_norm = pivot.div(pivot.max(axis=1), axis=0)
fig2, ax2 = plt.subplots(figsize=(15,8))
sns.heatmap(pivot_norm.T, cmap='YlGnBu', cbar_kws={'label':'Normalized Volume'}, ax=ax2)
st.pyplot(fig2)

# --- Enhanced AI Commentary ---
st.subheader("🧠 CIO-Level Market Commentary")

latest_vol = pivot.iloc[-1]
yoy_change = ((pivot.iloc[-1] - pivot.iloc[-13]) / pivot.iloc[-13]).replace([float('inf'), -float('inf')], 0).fillna(0)
status = []
for sector in pivot.columns:
    delta = yoy_change.get(sector, 0)
    if delta > 0.2:
        status.append((sector, "🚀 Accumulation"))
    elif delta < -0.1:
        status.append((sector, "🔻 Distribution"))
    elif 0.05 < delta <= 0.15:
        status.append((sector, "🕵️ Stealth Buying"))
    else:
        status.append((sector, "Stable"))

top_sector = latest_vol.idxmax()
accumulating = [s for s, stat in status if stat == "🚀 Accumulation"]
distributing = [s for s, stat in status if stat == "🔻 Distribution"]
stealth = [s for s, stat in status if stat == "🕵️ Stealth Buying"]

commentary = f'''
### 1️⃣ Executive Summary
Institutional flows are currently favoring **{top_sector}**, leading sector volumes this month. 

### 2️⃣ Current Sector Dynamics
- **Accumulating Sectors**: {', '.join(accumulating) if accumulating else 'None'}
- **Distribution Observed**: {', '.join(distributing) if distributing else 'None'}
- **Stealth Buying Signals**: {', '.join(stealth) if stealth else 'None'}

### 3️⃣ Tactical Implications
- **Overweight**: {', '.join(accumulating) if accumulating else 'No clear candidates'}
- **Underweight**: {', '.join(distributing) if distributing else 'None'}
- **Watch for Breakouts**: {', '.join(stealth) if stealth else 'No stealth activity detected'}

### 4️⃣ Stock Picking Guidance
Focus analyst screening on sectors in accumulation:
- Look for strong balance sheets, dividend stability in Financials.
- In Industrials, prioritize firms with cyclical upside.
- Monitor Healthcare for undervalued plays amid stealth volume rises.

*Review charts above for visual confirmation of rotation patterns.*
'''

st.markdown(commentary)
st.success("Updated with professional AI-generated insights.")
