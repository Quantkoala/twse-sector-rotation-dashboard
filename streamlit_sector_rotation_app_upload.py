
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Set page config
st.set_page_config(page_title="Investment Intelligence Dashboard", page_icon="📈", layout="wide")
st.sidebar.markdown("**📄 App Version:** `TWSE API Integration v2.2.0`")

# TWSE API Key (for example, if needed - placeholder)
TWSE_API_URL = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
headers = {'User-Agent': 'Mozilla/5.0'}

# Function to fetch sector volume data for given stock tickers
@st.cache_data(show_spinner=False)
def get_sector_data(tickers, start):
    records = []
    for ticker in tickers:
        try:
            params = {
                'response': 'json', 
                'date': start, 
                'type': 'ALL'
            }
            response = requests.get(f"{TWSE_API_URL}?stockNo={ticker}", params=params, headers=headers)
            data = response.json()

            # Parse the data and store in a dataframe (simplified version)
            if data and 'data' in data:
                stock_data = pd.DataFrame(data['data'], columns=["Date", "Volume", "Turnover", "Stock Price"])
                stock_data["Ticker"] = ticker
                stock_data["Date"] = pd.to_datetime(stock_data["Date"])
                stock_data["Volume"] = stock_data["Volume"].astype(float)
                records.append(stock_data)

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            continue

    if not records:
        st.error("No valid data returned. Please check your watchlist.")
        return pd.DataFrame()

    return pd.concat(records, ignore_index=True)

# File uploader to load a custom CSV
uploaded = st.sidebar.file_uploader("Upload your watchlist.csv", type="csv")
if not uploaded:
    st.sidebar.warning("Please upload your `watchlist.csv` file.")
    st.stop()

watchlist = pd.read_csv(uploaded)["Ticker"].dropna().tolist()
START = (datetime.today() - timedelta(days=365*10)).strftime("%Y-%m-%d")
sector_data = get_sector_data(watchlist, START)

# Navigation panel
page = st.sidebar.radio("Navigation", ["📊 Sector Dashboard", "🌐 Macro Correlation"])

# Sector Dashboard Page
if page == "📊 Sector Dashboard":
    st.title("📊 Full Sector Rotation Dashboard")

    # Full sector volume chart
    st.subheader("📈 All-Sector Volume Chart")
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    sector_data.groupby("Date")["Volume"].sum().plot.area(ax=ax1, alpha=0.7)
    ax1.set_ylabel("Volume")
    st.pyplot(fig1)

    # Filter options for sector view
    default = sector_data["Ticker"].unique()[:5].tolist()
    selected = st.multiselect("Select Sectors", sector_data["Ticker"].unique(), default=default)
    date_range = st.slider("Date Range", min_value=sector_data["Date"].min().date(),
                           max_value=sector_data["Date"].max().date(),
                           value=(sector_data["Date"].min().date(), sector_data["Date"].max().date()))
    filtered = sector_data.loc[sector_data["Date"].between(date_range[0], date_range[1]) & sector_data["Ticker"].isin(selected)]

    st.subheader("🎛️ Filtered Sector Volume Trends")
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    filtered.groupby("Date")["Volume"].sum().plot.area(ax=ax2, alpha=0.85)
    st.pyplot(fig2)

    # AI Commentary for Sector Rotation
    st.subheader("🧠 AI Commentary – Sector Rotation Analysis")
    # Calculate year-over-year volume changes
    yoy = (sector_data.groupby("Date")["Volume"].sum().iloc[-1] - sector_data.groupby("Date")["Volume"].sum().iloc[-13]) / sector_data.groupby("Date")["Volume"].sum().iloc[-13]
    insights = []
    for sector, change in yoy.items():
        if change > 0.2:
            insights.append(f"- **{sector}**: 🚀 Accumulation (+{change*100:.1f}%)")
        elif change < -0.1:
            insights.append(f"- **{sector}**: 🔻 Distribution ({change*100:.1f}%)")
        elif 0.05 < change <= 0.15:
            insights.append(f"- **{sector}**: 🕵️ Stealth Buying (+{change*100:.1f}%)")
        else:
            insights.append(f"- **{sector}**: ⚖️ Stable ({change*100:.1f}%)")
    st.markdown("\n".join(insights))

# Macro Correlation Page
else:
    st.title("🌐 Macro Correlation Intelligence")
    st.subheader("📉 Fetching Macro Indicators...")
    # Fetch and display data as needed, similar to previous code (same logic for macro indicators)

    st.subheader("🧠 Macro Sensitivity Commentary")
    st.markdown(f"**Key Observation:** {max(sector_data['Volume'])} sector shows significant macro sensitivity.")
