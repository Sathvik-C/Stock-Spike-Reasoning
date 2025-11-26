# backend/reasoning.py
import google.generativeai as genai
import os
from pathlib import Path
import toml
from typing import List, Dict

# 1. Load API Key
def load_gemini_key():
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        data = toml.load(secrets_path)
        return data.get("GEMINI_API_KEY")
    return os.getenv("GEMINI_API_KEY")


# 2. Single unified function to generate reasoning
def generate_reasoning(ticker: str, change: float, scored: List[Dict]) -> str:
    """
    FinBERT scores headlines → Gemini explains the movement.
    Only the MOST relevant headline is passed to AI.
    """

    direction = "rose" if change > 0 else "fell"
    magnitude = abs(change)

    if not scored or len(scored) == 0:
        return f"📌 **{ticker} {direction} {magnitude:.2f}%** — No recent news available for explanation."

    # Select BEST article depending on price direction
    if change > 0:     # positive movement → use positive sentiment if available
        best = max(scored, key=lambda x: x["score"])
    else:              # negative movement → choose most negative
        best = min(scored, key=lambda x: x["score"])

    article = best["title"]
    sentiment = best["sentiment"]
    score = best["score"]

    api_key = load_gemini_key()
    if not api_key:
        return (
            f"📌 **{ticker} {direction} {magnitude:.2f}%**\n"
            f"Key Trigger: **{article}**\n"
            f"Sentiment: **{sentiment} ({score:.2f})**\n"
            f"⚠ No Gemini API key — cannot generate explanation."
        )

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.5-pro")

    prompt = f"""
    You are a financial market analyst. Explain the stock movement clearly.

    Stock: {ticker}
    Price Movement: {magnitude}% ({direction})
    Key News Headline: "{article}"
    Sentiment Score: {sentiment} ({score:.2f})

    Generate a short and crisp explanation:
    • What could have caused the spike/drop?
    • Why does this specific headline matter?
    • Keep it factual, avoid speculation.
    • Keep it within 4-6 sentences.
    """

    try:
        response = model.generate_content(prompt)
        return f"📌 **{ticker} {direction} {magnitude:.2f}%**\n\n🧠 **Reason:**\n{response.text}"

    except Exception as e:
        return f"Gemini error → {e}"
