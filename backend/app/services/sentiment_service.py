"""Service for sentiment analysis using FinBERT (moved from finbert_sentiment.py)."""
from typing import Dict, List

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    _HAS_FINBERT = True
except Exception:
    torch = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    _HAS_FINBERT = False

MODEL_NAME = "ProsusAI/finbert"

_label_map = {
    0: "negative",
    1: "neutral",
    2: "positive",
}


class SentimentAnalyzer:
    """FinBERT-based sentiment analyzer for financial text."""
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.using_finbert = False

        if _HAS_FINBERT:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            self.using_finbert = True

    def _fallback_sentiment(self, text: str) -> Dict:
        lower = (text or "").lower()
        positive_words = ["beat", "growth", "surge", "rally", "upgrade", "profit", "gain", "strong"]
        negative_words = ["miss", "drop", "fall", "downgrade", "loss", "weak", "decline", "slump"]
        pos = sum(1 for w in positive_words if w in lower)
        neg = sum(1 for w in negative_words if w in lower)

        if pos > neg:
            return {"label": "positive", "label_prob": 0.7, "probs_list": [0.15, 0.15, 0.7], "sentiment_score": 0.55}
        if neg > pos:
            return {"label": "negative", "label_prob": 0.7, "probs_list": [0.7, 0.15, 0.15], "sentiment_score": -0.55}
        return {"label": "neutral", "label_prob": 0.8, "probs_list": [0.1, 0.8, 0.1], "sentiment_score": 0.0}
    
    def analyse_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of financial text.
        
        Returns:
            Dict with label, label_prob, probs_list, sentiment_score
        """
        if not text:
            return {
                "label": "neutral",
                "label_prob": 1.0,
                "probs_list": [0.0, 1.0, 0.0],
                "sentiment_score": 0.0,
            }

        if not self.using_finbert:
            return self._fallback_sentiment(text)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits[0]
        probs = torch.softmax(logits, dim=0)

        probs_list = probs.tolist()
        label_id = int(torch.argmax(probs))

        label = _label_map[label_id]
        label_prob = float(probs[label_id])
        sentiment_score = float(probs[2] - probs[0])

        return {
            "label": label,
            "label_prob": label_prob,
            "probs_list": probs_list,
            "sentiment_score": sentiment_score,
        }
    
    def batch_score(self, texts: List[str]) -> List[Dict]:
        """Score multiple texts efficiently."""
        return [self.analyse_sentiment(text) for text in texts]


from typing import Dict, Optional

_analyzer_instance: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance
