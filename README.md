# 📈 AI-Based Stock Movement Reason Finder (Gemini-Powered)

This project detects significant stock price movements and explains the reasons behind them using **Google Gemini API** for natural language reasoning. It fetches market data via **yfinance**, pulls related news, and leverages Gemini to describe *why* a stock moved sharply — all displayed in a simple **Streamlit dashboard**.

---

## 🚀 Features

- Detects large stock price spikes or drops (≥ 2–3% in 15 minutes)
- Fetches live stock data using **yfinance**
- Retrieves related financial news headlines
- Sends data to **Gemini API** for reasoning
- Interactive dashboard built with **Streamlit**

---

## 🧩 Project Structure

stock-reason-finder/
│
├── data/
│ ├── news_data.csv
│ ├── tweet_data.csv
│
├── app/
│ ├── main.py # Streamlit frontend
│ ├── reasoning_engine.py # Gemini API integration
│ ├── utils.py # Helper functions
│
├── config/
│ ├── api_keys.py # Gemini API key stored here
│
├── requirements.txt
├── README.md
└── LICENSE
