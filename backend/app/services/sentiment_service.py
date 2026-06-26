"""Service for sentiment analysis using FinBERT via Hugging Face Inference API."""
import os
import requests
from typing import Dict, List, Optional

# Remove torch and transformers dependencies
_HAS_FINBERT = False

MODEL_NAME = "ProsusAI/finbert"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

_label_map = {
    0: "positive",
    1: "negative",
    2: "neutral",
}

class SentimentAnalyzer:
    """FinBERT-based sentiment analyzer using HF Inference API."""
    
    def __init__(self):
        self.api_token = os.environ.get("HF_API_TOKEN")
        self.headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        self.using_api = bool(self.api_token)

    def _fallback_sentiment(self, text: str) -> Dict:
        lower = (text or "").lower()
        positive_words = ["beat", "growth", "surge", "rally", "upgrade", "profit", "gain", "strong", "higher"]
        negative_words = ["miss", "drop", "fall", "downgrade", "loss", "weak", "decline", "slump", "lower"]
        pos = sum(1 for w in positive_words if w in lower)
        neg = sum(1 for w in negative_words if w in lower)

        if pos > neg:
            return {"label": "positive", "label_prob": 0.7, "probs_list": [0.7, 0.15, 0.15], "sentiment_score": 0.55}
        if neg > pos:
            return {"label": "negative", "label_prob": 0.7, "probs_list": [0.15, 0.7, 0.15], "sentiment_score": -0.55}
        return {"label": "neutral", "label_prob": 0.8, "probs_list": [0.1, 0.1, 0.8], "sentiment_score": 0.0}
    
    def analyse_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of financial text via HF API."""
        if not text:
            return {"label": "neutral", "label_prob": 1.0, "probs_list": [0.0, 0.0, 1.0], "sentiment_score": 0.0}

        if not self.using_api:
            return self._fallback_sentiment(text)

        try:
            # We query the HF inference API
            response = requests.post(API_URL, headers=self.headers, json={"inputs": text, "wait_for_model": True}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                # The API returns a list of lists, like [[{'label': 'positive', 'score': 0.8}, ...]]
                if result and isinstance(result, list) and len(result) > 0:
                    scores = result[0]
                    # Convert to our format
                    probs = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                    for item in scores:
                        probs[item["label"]] = item["score"]
                    
                    # Sort to find the highest
                    best_label = max(probs, key=probs.get)
                    label_prob = probs[best_label]
                    sentiment_score = probs["positive"] - probs["negative"]
                    
                    return {
                        "label": best_label,
                        "label_prob": label_prob,
                        "probs_list": [probs["positive"], probs["negative"], probs["neutral"]],
                        "sentiment_score": sentiment_score,
                    }
        except Exception:
            pass
            
        return self._fallback_sentiment(text)
    
    def batch_score(self, texts: List[str]) -> List[Dict]:
        """Score multiple texts efficiently."""
        return [self.analyse_sentiment(text) for text in texts]


_analyzer_instance: Optional[SentimentAnalyzer] = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance
