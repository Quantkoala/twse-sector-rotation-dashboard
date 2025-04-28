from ace_tools import display_dataframe_to_user

# Generate the consolidated Streamlit dashboard script file
script_content = """
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# -------------------------------------------------- #
# Page Config & Version
# -------------------------------------------------- #
st.set_page_config(page_title="Investment Intelligence Dashboard",
                   page_icon="📈", layout="wide")
APP_VERSION = "v2.2.0 – Full Dashboard with Detailed Commentary"
st.sidebar.markdown(f"**📄 App Version:** `{APP_VERSION}`")

# -------------------------------------------------- #
# FRED API Helper
# -------------------------------------------------- #
FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"

@st.cache_data(show_spinner=False)
def fred_series(series_id: str, start_date: str) -> pd.Series:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = dict(
        series_id=series_id,
        api_key=FRED_API_KEY,
        file_type="json",
        observation_start=start_date
    )
    response = requests.get(url, params=params).json()
    df = pd.DataFrame(response["observations"])
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df["value"].rename(series_id)

# -------------------------------------------------- #
# Sector Volume Helper
# -------------------------------------------------- #
@st.cache_data(show_spinner=False)
def sector_volume(watchlist: list[str], start_date: str) -> pd.DataFrame:
    sess = requests_cache.CachedSession()
    records, sector_map = [], {}
    for ticker in watchlist:
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(start=start_date,
                              end=datetime.today(),
                              interval="1mo")[["Volume"]].reset_index()
            hist["Ticker"] = ticker
            records.append(hist)
            sector_map[ticker] = tk.info.get("industry", "Unknown")
        except Exception:
            continue
    df = pd.concat(records, ignore_index=True)
    df["Sector"] = df["Ticker"].map(sector_map)
    df["Date"] = pd.to_datetime(df["Date"]).dt.to_period("M").dt.to_timestamp()
    agg = df.groupby(["Date", "Sector"])["Volume"].sum().reset_index()
    return agg.pivot(index="Date", columns="Sector", values="Volume").fillna(0)

# -------------------------------------------------- #
# File Upload & Data Load
# -------------------------------------------------- #
uploaded = st.sidebar.file_uploader("Upload watchlist.csv", type="csv")
if not uploaded:
    st.sidebar.error("Please upload a watchlist.csv to proceed.")
    st.stop()

watchlist = pd.read_csv(uploaded)["Ticker"].dropna().tolist()
START = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
vol_df = sector_volume(watchlist, START)

# -------------------------------------------------- #
# Navigation
# -------------------------------------------------- #
page = st.sidebar.radio("📂 Navigation",
                        ["📊 Sector Dashboard", "🌐 Macro Correlation"],
                        index=0)

# -------------------------------------------------- #
# Sector Dashboard Page
# -------------------------------------------------- #
if page == "📊 Sector Dashboard":
    st.title("📊 TWSE Sector Rotation Dashboard")

    # Full chart
    st.subheader("🔷 All Sectors: Volume Trends")
    st.caption("Monthly trading volumes for all sectors in your watchlist")
    fig_all, ax_all = plt.subplots(figsize=(12, 5))
    vol_df.plot.area(ax=ax_all, alpha=0.7)
    ax_all.set_ylabel("Volume")
    st.pyplot(fig_all, use_container_width=True)

    # Filtered view
    default_sectors = vol_df.columns[:5].tolist()
    sel = st.multiselect("Filter by sectors", vol_df.columns.tolist(), default=default_sectors)
    rng = st.slider("Date range",
                    min_value=vol_df.index.min().date(),
                    max_value=vol_df.index.max().date(),
                    value=(vol_df.index.min().date(), vol_df.index.max().date()),
                    format="YYYY-MM")
    filt = vol_df.loc[rng[0]:rng[1], sel]

    st.subheader("🔷 Filtered Sector Volume Trends")
    st.caption("Filtered view based on your selection")
    fig_filt, ax_filt = plt.subplots(figsize=(12, 5))
    filt.plot.area(ax=ax_filt, alpha=0.85)
    st.pyplot(fig_filt, use_container_width=True)

    # Detailed AI commentary
    st.subheader("🧠 Detailed AI Commentary by Sector")
    yoy = (vol_df.iloc[-1] - vol_df.iloc[-13]) / vol_df.iloc[-13]
    status = {}
    for sec, delta in yoy.items():
        if delta > 0.2:
            status[sec] = f"🚀 Accumulation (YoY +{delta*100:.1f}%) — sustained institutional inflows."
        elif delta < -0.1:
            status[sec] = f"🔻 Distribution (YoY {delta*100:.1f}%) — profit-taking phase."
        elif 0.05 < delta <= 0.15:
            status[sec] = f"🕵️ Stealth Buying (YoY +{delta*100:.1f}%) — quiet build-up by smart money."
        else:
            status[sec] = f"⚖️ Stable (YoY {delta*100:.1f}%) — no clear rotation signal."

    commentary_lines = [f"- **{sec}**: {stat}" for sec, stat in status.items()]
    st.markdown("\\n".join(commentary_lines))

# -------------------------------------------------- #
# Macro Correlation Page
# -------------------------------------------------- #
else:
    st.title("🌐 Macro ↔ Sector Correlation Analysis")

    st.subheader("Fetching Macroeconomic Indicators")
    rate = fred_series("FEDFUNDS", START).rename("Fed Funds Rate")
    cpi = fred_series("CPIAUCSL", START).rename("CPI (YoY)")
    gdp = fred_series("GDP", START).rename("GDP (USD)")
    macro_df = pd.concat([rate, cpi, gdp], axis=1).ffill()

    combined = vol_df.join(macro_df, how="inner")
    corr = combined.corr().loc[["Fed Funds Rate", "CPI (YoY)", "GDP (USD)"], vol_df.columns]

    st.subheader("📊 Correlation Heatmap")
    st.caption("Correlation of sector volumes vs. macro indicators")
    fig_corr, ax_corr = plt.subplots(figsize=(12, 5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=ax_corr)
    st.pyplot(fig_corr, use_container_width=True)

    st.subheader("🧠 AI-Driven Insights")
    most = corr.abs().max().idxmax()
    st.markdown(f"**Key Insight:** *{most}* is currently most sensitive to macro shifts.")

"""

# Save to file
file_path = "/mnt/data/streamlit_dashboard_refined.py"
with open(file_path, "w") as f:
    f.write(script_content)

file_path
