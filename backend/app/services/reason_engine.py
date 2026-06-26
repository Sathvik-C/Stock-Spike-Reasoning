"""Rule-based reasoning engine for stock movement analysis."""
from typing import Dict, Tuple


class ReasonEngine:
    """Combines signals in priority order to determine primary reason for price movement."""
    
    def __init__(self):
        self.signal_priority = [
            "earnings_release",
            "major_news",
            "sector_rotation",
            "technical_breakout",
            "generic_momentum"
        ]
    
    def combine_signals(self, signals: Dict) -> Tuple[str, int, Dict]:
        """
        Combine multiple signals in priority order.
        
        Args:
            signals: Dict with keys from signal_priority
            
        Returns:
            (reason_category, confidence: 1-100, reason_detail: Dict)
        """
        earnings = signals.get("earnings_release") or {}
        if earnings.get("fired"):
            return "earnings_release", 95, earnings
        elif earnings.get("bse_headline"):
            # BSE filing fallback check
            return "earnings_release", 80, earnings

        major_news = signals.get("major_news") or {}
        if major_news.get("fired"):
            return "major_news", 85, major_news

        sector = signals.get("sector_rotation") or {}
        if sector.get("fired"):
            return "sector_rotation", 75, sector

        technical = signals.get("technical_breakout") or {}
        if technical.get("fired"):
            return "technical_breakout", 70, technical

        fallback = signals.get("generic_momentum") or {"fired": True}
        return "generic_momentum", 55, fallback
    
    def generate_summary(self, ticker: str, change_pct: float, reason: str, details: Dict) -> str:
        """
        Generate plain-English summary from template.
        
        Args:
            ticker: Stock ticker
            change_pct: Price change percentage
            reason: Reason category
            details: Detailed data for the reason
        
        Returns:
            Plain-English summary paragraph
        """
        direction = "rose" if change_pct >= 0 else "fell"
        base = f"{ticker} {direction} {abs(change_pct):.2f}% over the selected window."

        if reason == "earnings_release":
            beat_miss = details.get("beat_miss")
            pct = details.get("beat_miss_pct")
            bse_headline = details.get("bse_headline")
            
            if beat_miss and pct is not None:
                return f"{base} The move appears earnings-led, with a {beat_miss} of about {pct:.2f}% versus estimates."
            elif bse_headline:
                return f"{base} The move appears linked to a recent earnings update. {bse_headline}"
            return f"{base} The move appears linked to a recent earnings update."

        if reason == "major_news":
            headline = details.get("headline")
            if headline:
                return f"{base} The strongest near-term catalyst is recent news: {headline}"
            return f"{base} The move is likely driven by recent company-specific news flow."

        if reason == "sector_rotation":
            sector_ticker = details.get("sector_ticker", "sector index")
            sector_change = details.get("sector_change_pct")
            if sector_change is not None:
                return f"{base} Sector context is supportive: {sector_ticker} moved {sector_change:.2f}% in the same period."
            return f"{base} The move is aligned with broader sector rotation."

        if reason == "technical_breakout":
            return f"{base} Technical conditions support momentum continuation (price/volume and indicator alignment)."

        return f"{base} No single high-confidence catalyst dominated; this appears to be broad momentum-driven movement."
