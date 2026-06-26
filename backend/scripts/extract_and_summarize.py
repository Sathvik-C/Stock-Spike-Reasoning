"""Extract and summarize stock news articles using NewsData.io API and DistilBART.

Usage:
    python backend/scripts/extract_and_summarize.py <url1> <url2> ...

Example:
    python backend/scripts/extract_and_summarize.py https://www.reuters.com/markets/asia/infosys-results/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SERVICES_DIR = BACKEND_DIR / "app" / "services"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

import news_service as news_service_module


def build_articles_from_urls(urls: List[str]) -> List[Dict]:
    articles: List[Dict] = []
    for url in urls:
        print(f"\n[Extracting] {url}")
        paragraphs = news_service_module.extract_article_paragraphs(url, debug=True)
        # Join ALL paragraphs — not just the first one
        full_text = "\n\n".join(paragraphs).strip() if paragraphs else ""
        articles.append(
            {
                "title": "",
                "source": "",
                "url": url,
                "paragraphs": paragraphs,   # keep raw paragraphs for display
                "full_text": full_text,
            }
        )
    return articles


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and summarize article URLs")
    parser.add_argument("urls", nargs="+", help="One or more article URLs")
    args = parser.parse_args()

    articles = build_articles_from_urls(args.urls)
    summarization_service = _resolve_summarization_service()
    result = summarization_service.summarize_combined(articles)

    # ── Per-article output ────────────────────────────────────────────────
    for i, (article, result_article) in enumerate(zip(articles, result.get("articles", [])), 1):
        print(f"\n{'='*60}")
        print(f"Article {i}: {article.get('url', '')}")
        print(f"{'='*60}")

        paragraphs = article.get("paragraphs", [])
        if paragraphs:
            print(f"\n--- Extracted Paragraphs ({len(paragraphs)} total) ---\n")
            for j, para in enumerate(paragraphs, 1):
                print(f"[{j}] {para}\n")
        else:
            print("\n--- Extracted Paragraphs ---\n(none found)\n")

        print(f"--- Per-Article Summary ---\n")
        summary = result_article.get("summary")
        scraped = result_article.get("scraped", False)
        if scraped and summary:
            print(summary)
        elif not scraped:
            print("(skipped — could not extract enough content)")
        else:
            print("(no summary generated)")

    # ── Overall summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("OVERALL SUMMARY")
    print(f"{'='*60}\n")
    print(result.get("overall_summary") or "(no overall summary)")
    print(f"\nArticles passed in : {result.get('article_count', 0)}")
    print(f"Successfully processed: {result.get('summarized_count', 0)}")


def _resolve_summarization_service():
    try:
        from summarization_service import get_summarization_service
        return get_summarization_service()
    except ImportError:
        from app.services.summarization_service import get_summarization_service
        return get_summarization_service()


if __name__ == "__main__":
    main()
