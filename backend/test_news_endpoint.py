import requests
try:
    resp = requests.get("http://127.0.0.1:8000/api/stocks/INFY.NS/news-summary", timeout=30)
    print("Status:", resp.status_code)
    print("Text:", resp.text[:500])
except Exception as e:
    print("Error:", e)
