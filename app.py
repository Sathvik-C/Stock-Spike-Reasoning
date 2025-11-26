# ===============================================================
# IMPORTS
# ===============================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict
from datetime import datetime

# BACKEND IMPORTS
from backend.spike_detector import get_recent_data
from backend.news_fetcher import fetch_news
from backend.finbert_sentiment import analyse_sentiment
from backend.reasoning import generate_reasoning
from backend.top_movers import get_top_movers
from utils.nifty100 import NIFTY100, NIFTY100_NAMES

# ===============================================================
# UI CONFIG
# ===============================================================
st.set_page_config(
    page_title="Stock Spike Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================================================
# CUSTOM CSS
# ===============================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }
    .main {
        background: radial-gradient(circle at 20% 20%, #1b2640, #05060a 60%);
        color: #f4f4f6;
    }
    .hero-card {
        background: linear-gradient(120deg, rgba(79,139,249,0.15), rgba(147,112,219,0.2));
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(5, 6, 10, 0.35);
    }
    .stock-card {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 18px;
        padding: 1.5rem;
        margin: 1.25rem 0;
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(8px);
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    .stock-card:hover {
        transform: translateY(-4px);
        border-color: rgba(79, 139, 249, 0.6);
        box-shadow: 0 18px 30px rgba(0, 0, 0, 0.35);
    }
    .metric-card {
        background: rgba(15, 22, 35, 0.75);
        padding: 1.2rem 1.5rem;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-align: center;
    }
    .metric-label {
        color: #b5bfd9;
        font-size: 0.9rem;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.9rem;
        font-weight: 700;
    }
    .news-item {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #4f8bf9;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0 10px 10px 0;
    }
    .ai-analysis {
        background: rgba(147, 112, 219, 0.12);
        padding: 1.25rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        border-left: 4px solid #9370DB;
    }
    .section-title {
        color: #e5e8ff;
        letter-spacing: 0.02em;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .streamlit-expanderContent {
        background: rgba(0, 0, 0, 0.15);
        border-radius: 0 0 12px 12px;
    }
    .positive {
        color: #0f9d58;
    }
    .negative {
        color: #f44336;
    }
    .neutral {
        color: #ffb347;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================
# FINBERT HEADLINE SCORING
# ===============================================================
def score_headlines(headlines: List[Dict]) -> List[Dict]:
    scored = []
    for h in headlines:
        sentiment, _, _, sentiment_score = analyse_sentiment(h['title'])
        scored.append({
            **h,
            'sentiment': sentiment,
            'score': sentiment_score
        })
    return scored


def set_detail_from_gainer():
    value = st.session_state.get("gainer_select")
    placeholder = st.session_state.get("gainer_placeholder")
    if value and placeholder and value != placeholder:
        st.session_state["detail_choice"] = value


def set_detail_from_loser():
    value = st.session_state.get("loser_select")
    placeholder = st.session_state.get("loser_placeholder")
    if value and placeholder and value != placeholder:
        st.session_state["detail_choice"] = value


def render_stock_detail(ticker: str, change: float, days_window: int) -> None:
    """Render the interactive detail card for a single stock, fetching price data on demand."""
    company_name = NIFTY100_NAMES.get(ticker, ticker.replace('.NS', ''))
    symbol = ticker.replace('.NS', '')
    accent = "#0f9d58" if change >= 0 else "#f44336"
    change_str = f"{change:+.2f}%"

    price_cache = st.session_state.setdefault("price_cache", {})
    cached = price_cache.get(ticker)

    if cached and cached["days"] == days_window:
        df = cached["data"]
    else:
        df = get_recent_data(ticker, period=f"{days_window}d")
        if df is None or df.empty or "Close" not in df:
            st.warning("Price data unavailable for this ticker right now.")
            return
        price_cache[ticker] = {"days": days_window, "data": df}

    closes = df["Close"].astype(float)
    y_min = closes.min()
    y_max = closes.max()
    padding = max((y_max - y_min) * 0.08, 0.5)
    y_min -= padding
    y_max += padding

    with st.container():
        st.markdown(f"""
        <div class='stock-card'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;'>
                <div>
                    <h2 style='margin: 0;'>{symbol}</h2>
                    <p style='color: #9e9e9e; margin: 0;'>{company_name}</p>
                </div>
                <span style='font-size: 1.5rem; font-weight: 600; color: {accent};'>{change_str}</span>
            </div>
        """, unsafe_allow_html=True)

        fig = go.Figure(go.Scatter(
            x=df.index,
            y=closes,
            mode="lines",
            line=dict(width=2.5, color=accent),
            name="Price"
        ))
        fig.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showline=True, linecolor='#2d3748'),
            yaxis=dict(
                showgrid=True,
                gridcolor='#2d3748',
                showline=True,
                linecolor='#2d3748',
                range=[y_min, y_max]
            )
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with st.spinner(f"🔍 Analyzing {ticker}..."):
            news = fetch_news(ticker, max_headlines=6)
            scored = score_headlines(news)[:3] if news else []

            with st.expander("📰 View News & Analysis", expanded=True):
                if scored:
                    st.markdown("#### Top Headlines")
                    for h in scored:
                        emoji = "🟢" if h["sentiment"] == "positive" else "🔴" if h["sentiment"] == "negative" else "🟡"
                        st.markdown(f"""
                        <div class='news-item'>
                            <div style='margin-bottom: 0.5rem; font-weight: 500;'>{h['title']}</div>
                            <div style='font-size: 0.85rem; color: #9e9e9e;'>
                                {emoji} {h['sentiment'].title()} (Score: {h['score']:.2f}) • 
                                <span style='font-size: 0.8em;'>{h.get('source', 'Unknown')}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent news found for this stock.")

                ai_analysis = generate_reasoning(ticker, change, scored)
                st.markdown(f"""
                <div class='ai-analysis'>
                    <h4 style='margin-top: 0; color: #9370DB;'>🧠 FinBERT Reasoning</h4>
                    {ai_analysis}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

# ===============================================================
# STATE SETUP
# ===============================================================
if "analysis_data" not in st.session_state:
    st.session_state["analysis_data"] = None
if "analysis_meta" not in st.session_state:
    st.session_state["analysis_meta"] = {}
if "detail_choice" not in st.session_state:
    st.session_state["detail_choice"] = None

# Header
st.markdown("""
    <div class='hero-card' style='margin-bottom: 2rem;'>
        <h1 style='color: #ffffff; margin-bottom: 0.5rem;'>📈 Stock Spike Analyzer</h1>
        <p style='color: #d5d9f3; font-size: 1.05rem; margin-bottom: 1rem;'>
            AI-powered, sentiment-aware breakdown of the latest movements inside the NIFTY100 universe.
        </p>
        <div style='display: flex; gap: 1rem; flex-wrap: wrap;'>
            <span style='padding: 0.35rem 1rem; border-radius: 999px; background: rgba(79,139,249,0.25); color: #bcd5ff;'>FinBERT Sentiment</span>
            <span style='padding: 0.35rem 1rem; border-radius: 999px; background: rgba(15,157,88,0.2); color: #c6f6d5;'>FinBERT Reasoning</span>
            <span style='padding: 0.35rem 1rem; border-radius: 999px; background: rgba(255, 255, 255, 0.08); color: #f4f4f6;'>Top Movers Monitor</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# ===================== SIDEBAR =====================
with st.sidebar:
    st.markdown("## ⚙️ Analysis Settings")
    days_range = st.slider(
        "Select Lookback Period (Days)", 
        1, 30, 7,
        help="Number of days to analyze for stock movements"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Data Sources")
    st.markdown("""
        - **Stock Data**: Yahoo Finance
        - **News**: Yahoo News
        - **Sentiment**: FinBERT
        - **AI Analysis**: FinBERT Analysis
    """)
    
    st.markdown("---")
    st.markdown("### 📌 How to Use")
    st.markdown("""
    1. Click "Analyze NIFTY100" to fetch data
    2. View top gainers and losers
    3. Check news sentiment and AI analysis
    """)

# ===============================================================
# MAIN PROCESS BUTTON
# ===============================================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    start = st.button(
        "🚀 Analyze NIFTY100 Stocks", 
        use_container_width=True,
        type="primary",
        help="Click to analyze the top movers in NIFTY100"
    )

analysis_results = None
analysis_meta = st.session_state.get("analysis_meta", {})

if start:
    with st.spinner("🔍 Fetching stock data. This may take a moment..."):
        movers = get_top_movers(NIFTY100, days=days_range, top_n=5)

    if not movers or ("error" in movers):
        err_msg = movers.get("error") if isinstance(movers, dict) else "Please try again later."
        st.error(f"❌ Unable to fetch movers data. {err_msg}")
        st.stop()

    movement_dict = movers.get("movement", {})
    if not movement_dict:
        st.error("❌ No movement data available. Please try again later.")
        st.stop()

    df_changes = pd.DataFrame([
        {"Ticker": ticker, "Change%": change}
        for ticker, change in movement_dict.items()
    ])
    df_changes.sort_values(by="Change%", ascending=False, inplace=True)

    timestamp = datetime.now().strftime('%I:%M %p')
    st.session_state["analysis_data"] = df_changes.to_dict(orient="records")
    st.session_state["analysis_meta"] = {
        "days_range": days_range,
        "timestamp": timestamp
    }
    st.session_state["detail_choice"] = None
    st.session_state["gainer_placeholder"] = "Select a gainer"
    st.session_state["loser_placeholder"] = "Select a loser"
    st.session_state["gainer_select"] = st.session_state["gainer_placeholder"]
    st.session_state["loser_select"] = st.session_state["loser_placeholder"]
    st.success("Data refreshed successfully!", icon="✅")

analysis_results = st.session_state.get("analysis_data")
analysis_meta = st.session_state.get("analysis_meta", {})

if not analysis_results:
    st.info("Adjust the settings on the left and click “Analyze NIFTY100 Stocks” to view results.")
    st.stop()

effective_days = analysis_meta.get("days_range", days_range)
timestamp_display = analysis_meta.get("timestamp", datetime.now().strftime('%I:%M %p'))
st.caption(f"Window analyzed: last {effective_days} day(s) • Updated at {timestamp_display}")

df_changes = pd.DataFrame(analysis_results).dropna(subset=["Change%"])
if df_changes.empty:
    st.error("❌ Unable to compute price changes due to missing data. Please try again later.")
    st.stop()
df_changes.sort_values(by="Change%", ascending=False, inplace=True)

# ============================================================
# ⚡ QUICK MARKET PULSE
# ============================================================
top_gainer = df_changes.iloc[0]
top_loser = df_changes.iloc[-1]
avg_move = df_changes["Change%"].mean()
volatility = df_changes["Change%"].std()

st.markdown("### ⚡ Market Pulse", help="Fresh snapshot of how NIFTY100 moved in the selected period.")
pulse_cols = st.columns(4)
pulse_cols[0].markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Top Gainer</div>
        <div class='metric-value positive'>+{top_gainer['Change%']:.2f}%</div>
        <div style='font-size:0.85rem;'>{top_gainer['Ticker'].replace('.NS', '')}</div>
    </div>
""", unsafe_allow_html=True)
pulse_cols[1].markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Top Loser</div>
        <div class='metric-value negative'>{top_loser['Change%']:.2f}%</div>
        <div style='font-size:0.85rem;'>{top_loser['Ticker'].replace('.NS', '')}</div>
    </div>
""", unsafe_allow_html=True)
pulse_cols[2].markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Avg. Move</div>
        <div class='metric-value'>{avg_move:+.2f}%</div>
        <div style='font-size:0.85rem;'>Across all tracked tickers</div>
    </div>
""", unsafe_allow_html=True)
pulse_cols[3].markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Volatility</div>
        <div class='metric-value'>{volatility:.2f}%</div>
        <div style='font-size:0.85rem;'>Std. dev of move %</div>
    </div>
""", unsafe_allow_html=True)

# ============================================================
# TOP MOVERS OVERVIEW
# ============================================================
gainers = df_changes.head(5).copy()
losers = df_changes.tail(5).sort_values(by="Change%").copy()

def build_summary_table(data: pd.DataFrame) -> pd.DataFrame:
    table = pd.DataFrame({
        "Ticker": data["Ticker"].str.replace(".NS", ""),
        "Company": data["Ticker"].apply(lambda t: NIFTY100_NAMES.get(t, t.replace('.NS', ''))),
        "Change": data["Change%"].map(lambda x: f"{x:+.2f}%")
    })
    return table

st.markdown("---")
st.markdown("## 📊 Top Movers Overview")
summary_cols = st.columns(2)
with summary_cols[0]:
    st.markdown("#### 🚀 Top 5 Gainers")
    st.dataframe(
        build_summary_table(gainers),
        hide_index=True,
        use_container_width=True
    )
with summary_cols[1]:
    st.markdown("#### 📉 Top 5 Losers")
    st.dataframe(
        build_summary_table(losers),
        hide_index=True,
        use_container_width=True
    )

def make_label(ticker: str) -> str:
    pct = df_changes.loc[df_changes["Ticker"] == ticker, "Change%"].iloc[0]
    return f"{ticker.replace('.NS','')} ({pct:+.2f}%)"

gainers_list = list(gainers["Ticker"])
losers_list = list(losers["Ticker"])

st.markdown("---")
st.markdown("## 🎯 Select a Stock to Inspect")
selector_cols = st.columns(2)

gainer_placeholder = st.session_state.get("gainer_placeholder", "Select a gainer")
loser_placeholder = st.session_state.get("loser_placeholder", "Select a loser")

st.session_state.setdefault("gainer_select", gainer_placeholder)
st.session_state.setdefault("loser_select", loser_placeholder)

with selector_cols[0]:
    st.markdown("#### 🚀 Gainers")
    st.selectbox(
        "Pick a gainer",
        options=[gainer_placeholder] + gainers_list,
        format_func=lambda t: t if t == gainer_placeholder else make_label(t),
        key="gainer_select",
        on_change=set_detail_from_gainer
    )
with selector_cols[1]:
    st.markdown("#### 📉 Losers")
    st.selectbox(
        "Pick a loser",
        options=[loser_placeholder] + losers_list,
        format_func=lambda t: t if t == loser_placeholder else make_label(t),
        key="loser_select",
        on_change=set_detail_from_loser
    )

detail_choice = st.session_state.get("detail_choice")
if detail_choice and detail_choice in df_changes["Ticker"].values:
    selected_row = df_changes[df_changes["Ticker"] == detail_choice].iloc[0]
    st.markdown("---")
    st.markdown(f"## 🔍 Detailed View · {detail_choice.replace('.NS','')}")
    render_stock_detail(
        ticker=selected_row["Ticker"],
        change=selected_row["Change%"],
        days_window=effective_days
    )
else:
    st.info("Select any stock from the gainers or losers list above to load its chart and headlines.")

# ===============================================================
# FOOTER
# ===============================================================

st.markdown("""
<hr style='border: 1px solid #2d3748; margin: 2rem 0;'/>
<div style='text-align: center; color: #9e9e9e; font-size: 0.9rem;'>
    <p>Built with ❤️ using Streamlit, yfinance, and FinBERT Reasoning • Updated: {date}</p>
</div>
""".format(date=datetime.now().strftime("%B %d, %Y")), unsafe_allow_html=True)

