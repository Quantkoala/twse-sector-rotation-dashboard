
# Streamlit dashboard with full sector chart, filters, macro correlation and expanded AI commentary
# Version: v2.2.0 – Hedge Fund-Style Dashboard

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

st.set_page_config(page_title="Investment Intelligence Dashboard", page_icon="📈", layout="wide")
st.sidebar.markdown("**📄 App Version:** `v2.2.0 – Hedge Fund-Style Dashboard`")

FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"

@st.cache_data(show_spinner=False)
def fetch_fred_series(series_id, start):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start
    }
    resp = requests.get(url, params=params)
    df = pd.DataFrame(resp.json()["observations"])
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df["value"].rename(series_id)

@st.cache_data(show_spinner=False)
def get_sector_volume(tickers, start):
    records, sectors = [], {}
    session = requests_cache.CachedSession()
    for tkr in tickers:
        try:
            tk = yf.Ticker(tkr)
            hist = tk.history(start=start, end=datetime.today(), interval="1mo")[["Volume"]].reset_index()
            hist["Ticker"] = tkr
            records.append(hist)
            sectors[tkr] = tk.info.get("industry", "Unknown")
        except: continue
    df = pd.concat(records, ignore_index=True)
    df["Sector"] = df["Ticker"].map(sectors)
    df["Date"] = pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    grouped = df.groupby(["Date", "Sector"])["Volume"].sum().reset_index()
    return grouped.pivot(index="Date", columns="Sector", values="Volume").fillna(0)

uploaded = st.sidebar.file_uploader("Upload your watchlist.csv", type="csv")
if not uploaded:
    st.sidebar.warning("Please upload your `watchlist.csv` file.")
    st.stop()

watchlist = pd.read_csv(uploaded)["Ticker"].dropna().tolist()
START = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
vol = get_sector_volume(watchlist, START)

page = st.sidebar.radio("Navigation", ["📊 Sector Dashboard", "🌐 Macro Correlation"])

if page == "📊 Sector Dashboard":
    st.title("📊 Full Sector Rotation Dashboard")

    st.subheader("📈 All-Sector Volume Chart")
    st.caption("Showing full 10-year rotation across all sectors from your watchlist")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    vol.plot.area(ax=ax1, alpha=0.7)
    ax1.set_ylabel("Volume")
    st.pyplot(fig1)

    default = vol.columns[:5].tolist()
    selected = st.multiselect("Select Sectors", vol.columns.tolist(), default=default)
    date_range = st.slider("Date Range", min_value=vol.index.min().date(),
                           max_value=vol.index.max().date(),
                           value=(vol.index.min().date(), vol.index.max().date()))
    filtered = vol.loc[date_range[0]:date_range[1], selected]

    st.subheader("🎛️ Filtered Sector Volume Trends")
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    filtered.plot.area(ax=ax2, alpha=0.85)
    ax2.set_ylabel("Volume")
    st.pyplot(fig2)

    st.subheader("🔥 Sector Volume Heatmap")
    norm = filtered.div(filtered.max(axis=1), axis=0)
    fig3, ax3 = plt.subplots(figsize=(15, 6))
    sns.heatmap(norm.T, cmap="YlGnBu", cbar_kws={"label": "Intensity"}, ax=ax3)
    st.pyplot(fig3)

    st.subheader("🧠 AI Commentary – Sector Rotation Analysis")
    yoy = (vol.iloc[-1] - vol.iloc[-13]) / vol.iloc[-13]
    insights = []
    for sec, change in yoy.items():
        if change > 0.2:
            insights.append(f"- **{sec}**: 🚀 Accumulation (+{change*100:.1f}%) – likely institutional buildup.")
        elif change < -0.1:
            insights.append(f"- **{sec}**: 🔻 Distribution ({change*100:.1f}%) – possible profit taking.")
        elif 0.05 < change <= 0.15:
            insights.append(f"- **{sec}**: 🕵️ Stealth Buying (+{change*100:.1f}%) – rising quietly.")
        else:
            insights.append(f"- **{sec}**: ⚖️ Stable ({change*100:.1f}%) – neutral activity.")
    st.markdown("\n".join(insights))

else:
    st.title("🌐 Macro Correlation Intelligence")
    st.subheader("📉 Fetching Macro Indicators...")
    rate = fetch_fred_series("FEDFUNDS", START).rename("Fed Funds Rate")
    cpi = fetch_fred_series("CPIAUCSL", START).rename("CPI")
    gdp = fetch_fred_series("GDP", START).rename("GDP")
    macro = pd.concat([rate, cpi, gdp], axis=1).ffill()

    st.subheader("📊 Correlation Heatmap vs Macro")
    combined = vol.join(macro, how="inner")
    corr = combined.corr().loc[["Fed Funds Rate", "CPI", "GDP"], vol.columns]
    fig4, ax4 = plt.subplots(figsize=(12, 5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=ax4)
    st.pyplot(fig4)

    st.subheader("🧠 Macro Sensitivity Commentary")
    max_corr = corr.abs().max().idxmax()
    st.markdown(f"**Key Observation:** `{max_corr}` is the sector most responsive to macroeconomic shifts currently.")
