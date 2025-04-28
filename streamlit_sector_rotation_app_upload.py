
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

st.set_page_config(page_title="Investment Intelligence Dashboard", layout="wide")
APP_VERSION = "v2.1.0 - Macro Filters Upgrade"
st.sidebar.markdown(f"**📄 App Version:** `{APP_VERSION}`")

FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"
page = st.sidebar.radio("📂 Navigation", ["📊 Sector Dashboard", "🌐 Macro Correlation"])

@st.cache_data(show_spinner=False)
def fetch_fred_series(series_id, start_date):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json", "observation_start": start_date}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df[['value']].astype(float)
    df.rename(columns={'value': series_id}, inplace=True)
    return df

@st.cache_data(show_spinner=False)
def fetch_sector_data(tickers, start_macro):
    records = []
    sectors = {}
    with requests_cache.CachedSession():
        for tkr in tickers:
            try:
                tk = yf.Ticker(tkr)
                hist = tk.history(start=start_macro, end=datetime.today(), interval='1mo')[['Volume']].reset_index()
                hist['Ticker'] = tkr
                records.append(hist)
                sectors[tkr] = tk.info.get('industry', 'Unknown')
            except:
                continue
    df = pd.concat(records, ignore_index=True)
    df['Sector'] = df['Ticker'].map(sectors)
    df['Date'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
    agg = df.groupby(['Date','Sector'])['Volume'].sum().reset_index()
    pivot = agg.pivot(index='Date', columns='Sector', values='Volume').fillna(0)
    return pivot

uploaded_file = st.sidebar.file_uploader("Upload your watchlist.csv", type="csv")
if uploaded_file:
    watchlist = pd.read_csv(uploaded_file)['Ticker'].dropna().tolist()
else:
    st.sidebar.warning("Please upload a watchlist.csv to proceed.")
    st.stop()

start_macro = (datetime.today() - timedelta(days=365*10)).strftime('%Y-%m-%d')
sector_vol = fetch_sector_data(watchlist, start_macro)

if page == "📊 Sector Dashboard":
    st.title("📊 TWSE Sector Rotation Dashboard")
    selected_sectors = st.multiselect("Select Sectors", sector_vol.columns.tolist(), default=sector_vol.columns.tolist()[:5])
    date_range = st.slider("Select Date Range", min_value=sector_vol.index.min().date(), max_value=sector_vol.index.max().date(),
                           value=(sector_vol.index.min().date(), sector_vol.index.max().date()))
    filtered = sector_vol.loc[date_range[0]:date_range[1], selected_sectors]
    st.subheader("🔷 Filtered Sector Volume Trends")
    fig, ax = plt.subplots(figsize=(12,6))
    filtered.plot.area(ax=ax)
    st.pyplot(fig)
    st.subheader("🧠 AI Commentary")
    top_sector = filtered.iloc[-1].idxmax()
    st.markdown(f"**Observation:** Current rotation favors **{top_sector}** within selected sectors and timeframe.")

if page == "🌐 Macro Correlation":
    st.title("🌐 Macro ↔ Sector Correlation Analysis")
    st.info("Fetching macro data...")
    rate_df = fetch_fred_series("FEDFUNDS", start_macro)
    cpi_df = fetch_fred_series("CPIAUCSL", start_macro)
    gdp_df = fetch_fred_series("GDP", start_macro)
    macro_df = rate_df.join(cpi_df, how='outer').join(gdp_df, how='outer').fillna(method='ffill')
    combined = sector_vol.join(macro_df, how='inner')
    corr_matrix = combined.corr().loc[["FEDFUNDS", "CPIAUCSL", "GDP"], sector_vol.columns]
    st.subheader("📊 Correlation Heatmap")
    fig, ax = plt.subplots(figsize=(12,6))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
    st.pyplot(fig)
    st.subheader("🧠 AI Insight")
    st.markdown(f"**Key Insight:** Sector most sensitive to macro changes is **{corr_matrix.abs().max(axis=0).idxmax()}**.")
