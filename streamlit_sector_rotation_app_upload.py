
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# === Page Config ===
st.set_page_config(page_title="TWSE Investment Intelligence Dashboard", layout="wide")

# === Version Indicator ===
APP_VERSION = "v2.0.0 - Integrated Macro & Sector Dashboard"
st.sidebar.markdown(f"**📄 App Version:** `{APP_VERSION}`")

# === API Key for FRED ===
FRED_API_KEY = "d11aa169b82fc4ab22a64e20b8e35ecd"

# === Sidebar Navigation ===
page = st.sidebar.radio("📂 Navigation", ["📊 Sector Dashboard", "🌐 Macro Correlation"])

# === Common Data Fetching Functions ===
@st.cache_data(show_spinner=False)
def fetch_fred_series(series_id, start_date):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date
    }
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

# === File Upload ===
uploaded_file = st.sidebar.file_uploader("Upload your watchlist.csv", type="csv")
if uploaded_file:
    watchlist = pd.read_csv(uploaded_file)['Ticker'].dropna().tolist()
else:
    st.sidebar.warning("Please upload a watchlist.csv to proceed.")
    st.stop()

start_macro = (datetime.today() - timedelta(days=365*10)).strftime('%Y-%m-%d')

# === Sector Dashboard ===
if page == "📊 Sector Dashboard":
    st.title("📊 TWSE Sector Rotation Dashboard")

    sector_vol = fetch_sector_data(watchlist, start_macro)

    st.subheader("📈 Sector Volume Trends")
    fig, ax = plt.subplots(figsize=(12,6))
    sector_vol.plot.area(ax=ax)
    st.pyplot(fig)

    st.subheader("🔥 Sector Volume Intensity Heatmap")
    pivot_norm = sector_vol.div(sector_vol.max(axis=1), axis=0)
    fig2, ax2 = plt.subplots(figsize=(15,8))
    sns.heatmap(pivot_norm.T, cmap='YlGnBu', cbar_kws={'label':'Normalized Volume'}, ax=ax2)
    st.pyplot(fig2)

    st.subheader("🧠 CIO-Level Market Commentary")
    latest_vol = sector_vol.iloc[-1]
    yoy_change = ((sector_vol.iloc[-1] - sector_vol.iloc[-13]) / sector_vol.iloc[-13]).replace([float('inf'), -float('inf')], 0).fillna(0)
    status = []
    for sector in sector_vol.columns:
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
    '''
    st.markdown(commentary)

# === Macro Correlation Page ===
if page == "🌐 Macro Correlation":
    st.title("🌐 Macro ↔ Sector Correlation Analysis")

    st.info("Fetching macroeconomic data from FRED...")
    rate_df = fetch_fred_series("FEDFUNDS", start_macro)
    cpi_df = fetch_fred_series("CPIAUCSL", start_macro)
    macro_df = rate_df.join(cpi_df, how='outer').fillna(method='ffill')

    sector_vol = fetch_sector_data(watchlist, start_macro)
    combined = sector_vol.join(macro_df, how='inner')
    corr_matrix = combined.corr().loc[["FEDFUNDS", "CPIAUCSL"], sector_vol.columns]

    st.subheader("📊 Correlation Heatmap: Macro Indicators vs. Sector Volumes")
    fig, ax = plt.subplots(figsize=(12,6))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
    st.pyplot(fig)

    st.subheader("🧠 AI-Driven Insight")
    strong_corr = corr_matrix.apply(lambda x: x.abs()).max()
    top_sector_rate = strong_corr.idxmax()

    insight = (
        f"As of **{datetime.today().strftime('%Y-%m-%d')}**, the sector most sensitive to macro trends is **{top_sector_rate}**.\n\n"
        f"- **Interest Rate Correlation** peaks with: `{corr_matrix.loc['FEDFUNDS'].idxmax()}`.\n"
        f"- **Inflation Correlation** peaks with: `{corr_matrix.loc['CPIAUCSL'].idxmax()}`.\n\n"
        "This suggests rotation behavior is heavily influenced by current monetary policy and inflation dynamics."
    )
    st.markdown(insight)
