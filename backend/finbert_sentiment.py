# backend/finbert_sentiment.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load model once (cached)
MODEL_NAME = "ProsusAI/finbert"

_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

_label_map = {
    0: "negative",
    1: "neutral",
    2: "positive"
}

def analyse_sentiment(text: str):
    """
    Returns:
    label, label_prob, all_probs, sentiment_score
    sentiment_score = (positive_prob - negative_prob)
    """

    inputs = _tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = _model(**inputs)

    logits = outputs.logits[0]
    probs = torch.softmax(logits, dim=0)

    probs_list = probs.tolist()
    label_id = int(torch.argmax(probs))

    label = _label_map[label_id]
    label_prob = float(probs[label_id])

    sentiment_score = float(probs[2] - probs[0])  # positive - negative

    return label, label_prob, probs_list, sentiment_score
