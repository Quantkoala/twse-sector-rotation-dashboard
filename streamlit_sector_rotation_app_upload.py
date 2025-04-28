
import streamlit as st
import pandas as pd
import yfinance as yf
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

st.set_page_config(page_title="TWSE Sector Rotation Dashboard", layout="wide")

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
st.info("Fetching live data... This may take a moment for large watchlists.")

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
st.subheader("📈 Sector Volume Trends (Stacked Area Chart)")
pivot = agg_df.pivot(index='Date', columns='Sector', values='Volume').fillna(0)
fig, ax = plt.subplots(figsize=(12,6))
pivot.plot.area(ax=ax)
st.pyplot(fig)

st.subheader("🔥 Sector Volume Intensity Heatmap")
pivot_norm = pivot.div(pivot.max(axis=1), axis=0)
fig2, ax2 = plt.subplots(figsize=(15,8))
sns.heatmap(pivot_norm.T, cmap='YlGnBu', cbar_kws={'label':'Normalized Volume'}, ax=ax2)
st.pyplot(fig2)

# --- AI Commentary ---
st.subheader("🧠 AI-Generated Commentary")
top_sector = pivot.iloc[-1].idxmax()
recent_trends = pivot.iloc[-3:].mean().sort_values(ascending=False).head(3).index.tolist()

commentary = f'''
As of **{datetime.today().strftime('%Y-%m-%d')}**, trading volumes indicate a strong rotation towards **{top_sector}**.
Recent activity also highlights increased focus on: {', '.join(recent_trends)}.
Sectors showing declining volume trends may signal distribution or risk-off sentiment.
'''

st.markdown(commentary)

st.success("Dashboard updated with live data!")
