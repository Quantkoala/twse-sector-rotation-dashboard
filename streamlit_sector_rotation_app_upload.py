
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

st.set_page_config(page_title="TWSE Sector + Macro Dashboard", layout="wide")
st.sidebar.markdown("**App Version:** TWSE + Macro v2.3.0")

TWSE_API_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
HEADERS = {"User-Agent": "Mozilla/5.0"}
FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"

@st.cache_data(show_spinner=False)
def fetch_twse_data(ticker, month):
    date = month.strftime("%Y%m%d")
    params = {
        "response": "json",
        "date": date,
        "stockNo": ticker
    }
    try:
        r = requests.get(TWSE_API_URL, params=params, headers=HEADERS)
        data = r.json()
        if "data" not in data or not data["data"]:
            return pd.DataFrame()
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["Date"] = pd.to_datetime(df["Date"].str.replace("/", "-"), errors="coerce")
        df["Volume"] = pd.to_numeric(df["成交股數"].str.replace(",", ""), errors="coerce")
        df["Ticker"] = ticker
        return df[["Date", "Volume", "Ticker"]]
    except:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def get_combined_data(tickers, start_date):
    all_data = []
    months = pd.date_range(start=start_date, end=datetime.today(), freq="MS").to_pydatetime().tolist()
    for tkr in tickers:
        frames = [fetch_twse_data(tkr, m) for m in months]
        stock_df = pd.concat(frames, ignore_index=True)
        all_data.append(stock_df)
    df = pd.concat(all_data, ignore_index=True)
    return df.dropna(subset=["Date", "Volume"])

@st.cache_data(show_spinner=False)
def fetch_macro_fred(series_id, start):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start.strftime("%Y-%m-%d")
    }
    try:
        r = requests.get(url, params=params).json()
        df = pd.DataFrame(r["observations"])
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df["value"].rename(series_id)
    except:
        return pd.Series()

uploaded = st.sidebar.file_uploader("Upload your watchlist.csv (ticker numbers only)", type="csv")
if uploaded is None:
    st.sidebar.warning("Please upload your `watchlist.csv` file.")
    st.stop()

watchlist = pd.read_csv(uploaded)["Ticker"].dropna().astype(str).tolist()
START_DATE = datetime.today() - timedelta(days=365 * 3)
sector_data = get_combined_data(watchlist, START_DATE)
if sector_data.empty:
    st.error("No TWSE data found.")
    st.stop()

page = st.sidebar.radio("Navigation", ["📊 Sector Dashboard", "🌐 Macro Correlation"])

if page == "📊 Sector Dashboard":
    st.title("📊 TWSE Sector Volume Dashboard")
    st.subheader("🔷 Full Volume Chart")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    sector_data.groupby("Date")["Volume"].sum().plot(ax=ax1)
    ax1.set_ylabel("Volume")
    st.pyplot(fig1)

    st.subheader("🎛️ Filtered View")
    options = st.multiselect("Select Tickers", sorted(sector_data["Ticker"].unique()), default=watchlist[:5])
    dr = st.slider("Date Range", min_value=sector_data["Date"].min().date(),
                   max_value=sector_data["Date"].max().date(),
                   value=(sector_data["Date"].min().date(), sector_data["Date"].max().date()))
    filtered = sector_data[(sector_data["Ticker"].isin(options)) &
                           (sector_data["Date"].dt.date >= dr[0]) &
                           (sector_data["Date"].dt.date <= dr[1])]
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    for tkr in options:
        sub = filtered[filtered["Ticker"] == tkr]
        sub.groupby("Date")["Volume"].sum().plot(ax=ax2, label=tkr)
    ax2.set_ylabel("Volume")
    ax2.legend()
    st.pyplot(fig2)

    st.subheader("🧠 Sector Commentary")
    recent = sector_data[sector_data["Date"] > sector_data["Date"].max() - pd.Timedelta("30D")]
    avg_volume = recent.groupby("Ticker")["Volume"].mean().sort_values(ascending=False)
    st.markdown("### Top Active Sectors (Last 30 Days)")
    for tkr, vol in avg_volume.items():
        st.markdown(f"- **{tkr}**: Avg Volume = {int(vol):,}")

elif page == "🌐 Macro Correlation":
    st.title("🌐 Macro Sensitivity vs Volume")
    st.subheader("Fetching Macro Indicators (FRED)")

    fedfunds = fetch_macro_fred("FEDFUNDS", START_DATE).rename("Fed Funds Rate")
    cpi = fetch_macro_fred("CPIAUCSL", START_DATE).rename("CPI")
    gdp = fetch_macro_fred("GDP", START_DATE).rename("GDP")
    macro = pd.concat([fedfunds, cpi, gdp], axis=1).ffill()

    vol_pivot = sector_data.pivot_table(index="Date", columns="Ticker", values="Volume", aggfunc="sum").ffill()
    df_combined = vol_pivot.join(macro, how="inner")

    st.subheader("📊 Correlation Heatmap")
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    corr = df_combined.corr().loc[["Fed Funds Rate", "CPI", "GDP"], vol_pivot.columns]
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, ax=ax3)
    st.pyplot(fig3)

    st.subheader("🧠 AI Observation")
    max_corr = corr.abs().max().idxmax()
    st.markdown(f"**Most macro-sensitive ticker:** `{max_corr}` based on current volume correlations.")
