# streamlit_dashboard_refined.py
# v2.2.0 – Fully-polished UI, smart defaults, labelled macros

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# -------------------------------------------------- #
# Page config & version
# -------------------------------------------------- #
st.set_page_config(page_title="Investment Intelligence Dashboard",
                   page_icon="📈", layout="wide")
APP_VERSION = "v2.2.0 – Polished UI + Smart Defaults"
st.sidebar.markdown(f"**📄 App Version:** `{APP_VERSION}`")

# -------------------------------------------------- #
# FRED API helper
# -------------------------------------------------- #
FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"

@st.cache_data(show_spinner=False)
def fred_series(series_id: str, start_date: str) -> pd.Series:
    """Return a monthly series from FRED as a Pandas Series"""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = dict(
        series_id=series_id,
        api_key=FRED_API_KEY,
        file_type="json",
        observation_start=start_date
    )
    r = requests.get(url, params=params).json()
    df = pd.DataFrame(r["observations"])
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return pd.to_numeric(df["value"], errors="coerce").rename(series_id)

# -------------------------------------------------- #
# Sector-volume helper
# -------------------------------------------------- #
@st.cache_data(show_spinner=False)
def sector_volume(watchlist: list[str], start_date: str) -> pd.DataFrame:
    """Aggregate monthly volumes → sector-pivot table"""
    rows, sector_map = [], {}
    sess = requests_cache.CachedSession()
    for tkr in watchlist:
        try:
            tk = yf.Ticker(tkr)
            hist = tk.history(start=start_date,
                              end=datetime.today(),
                              interval="1mo")[["Volume"]].reset_index()
            hist["Ticker"] = tkr
            rows.append(hist)
            sector_map[tkr] = tk.info.get("industry", "Unknown")
        except Exception:
            continue
    df = pd.concat(rows, ignore_index=True)
    df["Sector"] = df["Ticker"].map(sector_map)
    df["Date"] = pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    agg = df.groupby(["Date", "Sector"])["Volume"].sum().reset_index()
    return agg.pivot(index="Date", columns="Sector", values="Volume").fillna(0)

# -------------------------------------------------- #
# File upload
# -------------------------------------------------- #
uploaded = st.sidebar.file_uploader("Upload **watchlist.csv**", type="csv")
if uploaded is None:
    st.sidebar.error("Upload your watchlist to continue.")
    st.stop()
watch = pd.read_csv(uploaded)["Ticker"].dropna().tolist()

START = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
vol_tbl = sector_volume(watch, START)

# -------------------------------------------------- #
# Navigation
# -------------------------------------------------- #
page = st.sidebar.radio(
    "📂 Navigation",
    ["📊 Sector Dashboard", "🌐 Macro Correlation"],
    index=0
)

# -------------------------------------------------- #
# — PAGE 1 — Sector Dashboard
# -------------------------------------------------- #
if page.startswith("📊"):

    st.title("📊 TWSE Sector Rotation Dashboard")

    # smart defaults
    default_secs = vol_tbl.columns[:5].tolist()
    sel_secs = st.multiselect("Select sectors to display",
                              vol_tbl.columns.tolist(),
                              default=default_secs)
    dr = st.slider("Select date range",
                   min_value=vol_tbl.index.min().date(),
                   max_value=vol_tbl.index.max().date(),
                   value=(vol_tbl.index.min().date(),
                          vol_tbl.index.max().date()),
                   format="YYYY-MM")

    filt = vol_tbl.loc[dr[0]:dr[1], sel_secs]

    # ----- Trends chart
    st.markdown("#### 🔷 Sector Volume Trends")
    st.caption("_Monthly trading volume for selected sectors_")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    filt.plot.area(ax=ax1, alpha=.85)
    ax1.set_ylabel("Volume")
    st.pyplot(fig1, use_container_width=True)

    # ----- Heatmap
    st.markdown("#### 🔥 Volume Intensity Heatmap")
    st.caption("_Normalized intensity (row-wise) by month_")
    heat = filt.div(filt.max(axis=1), axis=0)
    fig2, ax2 = plt.subplots(figsize=(15, 6))
    sns.heatmap(heat.T, cmap="YlGnBu", cbar_kws=dict(label="Intensity"), ax=ax2)
    st.pyplot(fig2, use_container_width=True)

    # ----- AI commentary
    st.markdown("#### 🧠 AI Commentary")
    top_sec = filt.iloc[-1].idxmax()
    yoy = ((filt.iloc[-1] - filt.iloc[-13]) / filt.iloc[-13]).replace([pd.NA, pd.NaT], 0)
    bullets = [
        f"**Top-volume sector:** {top_sec}",
        f"**12-month leader:** {yoy.idxmax()} (volume +{(yoy.max()*100):.1f}%)",
        f"**Biggest fade:** {yoy.idxmin()} (volume {(yoy.min()*100):.1f}%)"
    ]
    st.markdown("\n".join([f"- {b}" for b in bullets]))

# -------------------------------------------------- #
# — PAGE 2 — Macro Correlation
# -------------------------------------------------- #
else:
    st.title("🌐 Macro ↔ Sector Correlation Analysis")

    st.info("Auto-fetching macro indicators from FRED…")

    rate   = fred_series("FEDFUNDS", START).rename("Fed Funds Rate")
    cpi    = fred_series("CPIAUCSL", START).rename("CPI (YoY)")
    gdp    = fred_series("GDP", START).rename("GDP")
    macros = pd.concat([rate, cpi, gdp], axis=1).ffill()

    combined = vol_tbl.join(macros, how="inner")
    corr = combined.corr().loc[["Fed Funds Rate", "CPI (YoY)", "GDP"],
                               vol_tbl.columns]

    st.markdown("#### 📊 Correlation Heatmap")
    st.caption("_Correlation of sector volumes vs. macro indicators_")
    fig3, ax3 = plt.subplots(figsize=(12, 5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=ax3)
    st.pyplot(fig3, use_container_width=True)

    st.markdown("#### 🧠 AI Insight")
    most_sensitive = corr.abs().max().idxmax()
    st.markdown(f"""
**Key Insight:** _up-to-date correlations show_ **{most_sensitive}** _is currently the most macro-sensitive sector based on Fed Funds Rate, CPI, and GDP._  
""")
