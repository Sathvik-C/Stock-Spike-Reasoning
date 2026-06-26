from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve().parents[1] / "scripts" / "extract_and_summarize.py"
SPEC = spec_from_file_location("extract_and_summarize", SCRIPT_FILE)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeNewsService:
    def __init__(self):
        self.calls = []

    def extract_article_paragraphs(self, url):
        self.calls.append(url)
        return [
            f"Paragraph one from {url}.",
            "Paragraph two with enough content to be useful.",
        ]


class FakeSummarizationService:
    def __init__(self):
        self.articles_seen = None

    def summarize_articles(self, articles):
        self.articles_seen = articles
        return {
            "overall_summary": "Combined summary.",
            "articles": [
                {
                    "url": article["url"],
                    "summary": f"Summary for {article['url']}",
                }
                for article in articles
            ],
        }


def test_build_articles_from_urls_joins_extracted_paragraphs(monkeypatch):
    fake_news_service = FakeNewsService()
    monkeypatch.setattr(MODULE, "news_service_module", fake_news_service)

    urls = ["https://example.com/a", "https://example.com/b"]
    articles = MODULE.build_articles_from_urls(urls)

    assert fake_news_service.calls == urls
    assert articles[0]["full_text"] == "Paragraph one from https://example.com/a."
    assert articles[1]["full_text"] == "Paragraph one from https://example.com/b."


def test_main_routes_articles_into_summarizer(monkeypatch, capsys):
    fake_news_service = FakeNewsService()
    fake_summary_service = FakeSummarizationService()

    monkeypatch.setattr(MODULE, "news_service_module", fake_news_service)
    monkeypatch.setattr(MODULE, "get_summarization_service", lambda: fake_summary_service)
    monkeypatch.setattr(
        "sys.argv",
        ["extract_and_summarize.py", "https://example.com/article"],
    )

    MODULE.main()

    assert fake_summary_service.articles_seen is not None
    assert fake_summary_service.articles_seen[0]["url"] == "https://example.com/article"
    assert fake_summary_service.articles_seen[0]["full_text"].startswith("Paragraph one")

    output = capsys.readouterr().out
    assert "Combined summary." in output