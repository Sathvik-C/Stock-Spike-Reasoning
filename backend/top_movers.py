import yfinance as yf
import pandas as pd

def get_top_movers(tickers, days: int = 30, top_n: int = 5):
    """
    Get top N gainers and losers based on Open(first) vs Close(last).
    """
    try:
        period = f"{days}d"
        data = yf.download(tickers, period=period, interval="1d")
        data.index = data.index.tz_localize(None)  # remove tz info
        data = data.sort_index()  # ensure ascending order

        # Optional: reset to just date (if you don't need time)
        data.index = pd.to_datetime(data.index.date)

        if data.empty or "Open" not in data.columns or "Close" not in data.columns:
            return {"error": "No data found."}

        open_first = data["Open"].iloc[0]
        close_last = data["Close"].iloc[-1]



        # Debug print for each ticker
        print("\n=== Debug: First Open vs Last Close ===")
        for t in tickers:
            print(f"{t}: Open={open_first[t]:.2f}, Close={close_last[t]:.2f}")

        movement = ((close_last - open_first) / open_first) * 100
        movement = movement.sort_values(ascending=False)

        gainers = movement.head(top_n).to_dict()
        losers = movement.tail(top_n).to_dict()

        return {"gainers": gainers, "losers": losers}
    except Exception as e:
        return {"error": str(e)}
