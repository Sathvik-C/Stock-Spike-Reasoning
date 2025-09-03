import streamlit as st
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import pandas as pd

from backend.spike_detector import get_recent_data
from backend.news_fetcher import fetch_news_rss
from backend.reasoning import generate_reasoning
from utils.nifty100 import NIFTY100

# Load env
load_dotenv()
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="Stock Spike Reasoning", layout="wide")

st.title("📈 Stock Spike Reasoning ")
st.write("Shows Top 5 Gainers & Losers from NIFTY100 and explains major spikes using news + Gemini reasoning.")

# --- Day range ---
days_range = st.slider("Select Day Range for Analysis", 1, 30, 7)

if st.button("🔍 Analyze"):
    results = []

    with st.spinner("Fetching stock data for NIFTY100..."):
        for ticker in NIFTY100:
            df = get_recent_data(ticker, period=f"{days_range}d")
            if df is not None and not df.empty:
                if "Close" in df.columns:
                    change = round(((df["Close"].iloc[-1] - df["Open"].iloc[0]) / df["Open"].iloc[0]) * 100, 2)
                    print(f"{ticker} -> {change}%")
                    results.append((ticker, change, df))

    if not results:
        st.error("No stock data found.")
    else:
        df_changes = pd.DataFrame(results, columns=["Ticker", "Change%", "Data"])
        df_changes.sort_values(by="Change%", ascending=False, inplace=True)

        # --- Top 5 Gainers ---
        st.subheader("🚀 Top 5 Gainers")
        gainers = df_changes.head(5)
        st.dataframe(gainers[["Ticker", "Change%"]].round(2))

        for _, row in gainers.iterrows():
            ticker, change, df = row["Ticker"], row["Change%"], row["Data"]
            st.write(f"### {ticker} (+{change:.2f}%)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines+markers", name="Close Price"))
            fig.update_layout(title=f"{ticker} Closing Prices", xaxis_title="Date", yaxis_title="Price", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            headlines = fetch_news_rss(ticker, max_headlines=5)
            if headlines:
                st.subheader("📰 Latest News Headlines")
                for h in headlines:
                    st.markdown(f"- [{h['title']}]({h['link']})", unsafe_allow_html=True)

            stock_info = f"{ticker} gained {change:.2f}% in last {days_range} days."
            reasoning_text = generate_reasoning(stock_info, headlines, api_key=GEMINI_API_KEY)
            st.subheader("AI Summary")
            st.write(reasoning_text)

        # --- Top 5 Losers ---
        st.subheader("📉 Top 5 Losers")
        losers = df_changes.tail(5)
        st.dataframe(losers[["Ticker", "Change%"]].round(2))

        for _, row in losers.iterrows():
            ticker, change, df = row["Ticker"], row["Change%"], row["Data"]
            st.write(f"### {ticker} ({change:.2f}%)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines+markers", name="Close Price"))
            fig.update_layout(title=f"{ticker} Closing Prices", xaxis_title="Date", yaxis_title="Price", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            headlines = fetch_news_rss(ticker, max_headlines=5)
            if headlines:
                st.subheader("📰 Latest News Headlines")
                for h in headlines:
                    st.markdown(f"- [{h['title']}]({h['link']})", unsafe_allow_html=True)

            stock_info = f"{ticker} dropped {change:.2f}% in last {days_range} days."
            reasoning_text = generate_reasoning(stock_info, headlines, api_key=GEMINI_API_KEY)
            st.subheader("AI Summary")
            st.write(reasoning_text)

st.markdown("---")
st.caption("Built with Streamlit, yfinance, Plotly, Google News RSS, and Gemini API • Team: Sushrutha & Group")
