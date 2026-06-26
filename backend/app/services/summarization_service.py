"""Service for summarizing financial news using DistilBART.

Strategy:
- Combine paragraphs from all scraped articles into one block
- Deduplicate at sentence level before combining (removes cross-article repetition)
- Run one single distilbart pass on the combined text
- No per-article summaries — one clean combined summary
"""
import re
from typing import Dict, List, Optional

try:
    from transformers import pipeline
    _HAS_TRANSFORMERS = True
except Exception:
    pipeline = None
    _HAS_TRANSFORMERS = False

MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
FALLBACK_SUMMARY = "Summary unavailable — could not extract article content."

# Minimum combined word count to attempt summarization
MIN_WORDS_FOR_SUMMARY = 30


class SummarizationService:
    """DistilBART-based summarization — combines all articles, deduplicates, summarizes once."""

    def __init__(self):
        self.pipeline = None
        self.available = False

        if _HAS_TRANSFORMERS:
            try:
                self.pipeline = pipeline(
                    "summarization",
                    model=MODEL_NAME,
                    device=-1,  # CPU
                )
                self.available = True
            except Exception:
                self.pipeline = None
                self.available = False

    # ── Helpers ───────────────────────────────────────────────────────────

    def _fallback_summary(self, text: str) -> str:
        """Return first 3 sentences when model is unavailable."""
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
        result = ". ".join(sentences[:3])
        return result + "." if result and not result.endswith(".") else result

    def _run_pipeline(self, text: str) -> Optional[str]:
        """Run distilbart on text. Returns None on failure."""
        if not self.available or not self.pipeline or not text.strip():
            return None
        try:
            word_count = len(text.split())
            # distilbart max_length must be less than input length
            max_len = min(130, max(30, word_count // 2))
            min_len = min(30, max(10, word_count // 4))
            response = self.pipeline(
                text,
                max_length=max_len,
                min_length=min_len,
                do_sample=False,
                truncation=True,
            )
            if not response:
                return None
            return str(response[0].get("summary_text", "")).strip() or None
        except Exception:
            return None

    def _chunk_and_summarize(self, text: str, max_words: int = 800) -> str:
        """Handle texts longer than distilbart's token limit by chunking."""
        words = text.split()
        if len(words) <= max_words:
            result = self._run_pipeline(text)
            return result if result else self._fallback_summary(text)

        # Split into chunks, summarize each, then summarize the summaries
        chunks = [
            " ".join(words[i:i + max_words])
            for i in range(0, len(words), max_words)
        ]
        chunk_summaries = []
        for chunk in chunks:
            s = self._run_pipeline(chunk)
            if s:
                chunk_summaries.append(s)

        if not chunk_summaries:
            return self._fallback_summary(text)

        joined = " ".join(chunk_summaries)
        final = self._run_pipeline(joined)
        return final if final else joined

    def _normalize_sentence(self, sentence: str) -> str:
        """Normalize sentence for deduplication comparison."""
        return re.sub(r"[^a-z0-9 ]", "", sentence.lower()).strip()

    def _deduplicate_sentences(self, paragraphs: List[str]) -> str:
        """
        Split paragraphs into sentences, deduplicate across all of them,
        and return a single combined clean text block.

        This removes repetitive facts that appear across multiple articles
        (e.g. "net profit rose 20.9% YoY" repeated in 3 articles becomes 1 occurrence).
        """
        seen_normalized = set()
        unique_sentences = []

        for paragraph in paragraphs:
            # Split on period + space or period + end of string
            raw_sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
            for sentence in raw_sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 20:
                    continue
                normalized = self._normalize_sentence(sentence)
                if not normalized:
                    continue
                # Use first 80 chars of normalized as key to catch near-duplicates
                key = normalized[:80]
                if key not in seen_normalized:
                    seen_normalized.add(key)
                    unique_sentences.append(sentence)

        return " ".join(unique_sentences)

    # ── Public API ────────────────────────────────────────────────────────

    def summarize_combined(self, articles: List[Dict]) -> Dict:
        """
        Combine paragraphs from all scraped articles, deduplicate at sentence
        level, then run one single summarization pass.

        Args:
            articles: list of dicts with keys:
                - title (str)
                - source (str)
                - url or link (str)
                - paragraphs (List[str]) — extracted paragraphs
                - full_text (str) — joined paragraphs
                - scraped (bool)

        Returns:
            {
                "overall_summary": str,
                "articles": [{ title, source, url, scraped }],
                "article_count": int,
                "summarized_count": int,
                "combined_word_count": int,
            }
        """
        input_articles = articles or []
        output_articles = []
        all_paragraphs: List[str] = []
        summarized_count = 0

        for article in input_articles:
            title = str(article.get("title") or "")
            source = str(article.get("source") or "")
            url = str(article.get("resolved_url") or article.get("url") or article.get("link") or "")
            scraped = bool(article.get("scraped", False))
            paragraphs = article.get("paragraphs") or []

            if paragraphs:
                all_paragraphs.extend(paragraphs)
                summarized_count += 1

            output_articles.append({
                "title": title,
                "source": source,
                "url": url,
                "scraped": scraped,
            })

        # Deduplicate sentences across all articles then combine
        combined_text = self._deduplicate_sentences(all_paragraphs)
        word_count = len(combined_text.split())

        if summarized_count == 0 or word_count < MIN_WORDS_FOR_SUMMARY:
            overall_summary = FALLBACK_SUMMARY
        elif not self.available:
            overall_summary = self._fallback_summary(combined_text)
        else:
            overall_summary = self._chunk_and_summarize(combined_text)
            if not overall_summary:
                overall_summary = self._fallback_summary(combined_text)

        return {
            "overall_summary": overall_summary,
            "articles": output_articles,
            "article_count": len(input_articles),
            "summarized_count": summarized_count,
            "combined_word_count": word_count,
        }

    def summarize_text(self, text: str) -> str:
        """Convenience method for summarizing arbitrary text."""
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        if not self.available:
            return self._fallback_summary(cleaned)
        return self._chunk_and_summarize(cleaned)


from typing import Dict, List, Optional

_summarization_service_instance: Optional[SummarizationService] = None


def get_summarization_service() -> SummarizationService:
    global _summarization_service_instance
    if _summarization_service_instance is None:
        _summarization_service_instance = SummarizationService()
    return _summarization_service_instance