import yfinance as yf
import pandas as pd


def get_top_movers(tickers, days: int = 30, top_n: int = 5) -> dict:
    """
    Compute percentage change for each ticker over the period and return top/bottom movers.
    """
    try:
        period = f"{days}d"
        data = yf.download(tickers, period=period, interval="1d", group_by="column")
        if data.empty or "Open" not in data or "Close" not in data:
            return {"error": "No data found."}

        open_first = data["Open"].iloc[0]
        close_last = data["Close"].iloc[-1]
        movement = ((close_last - open_first) / open_first) * 100
        movement = movement.dropna().sort_values(ascending=False)

        gainers = movement.head(top_n).round(2)
        losers = movement.tail(top_n).sort_values(ascending=True).round(2)

        return {
            "gainers": gainers.to_dict(),
            "losers": losers.to_dict(),
            "movement": movement.round(2).to_dict(),
        }
    except Exception as e:
        return {"error": str(e)}
