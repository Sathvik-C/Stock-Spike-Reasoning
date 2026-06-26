from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SERVICE_FILE = Path(__file__).resolve().parents[1] / "app" / "services" / "summarization_service.py"
SPEC = spec_from_file_location("summarization_service", SERVICE_FILE)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

FALLBACK_OVERALL_SUMMARY = MODULE.FALLBACK_OVERALL_SUMMARY
SummarizationService = MODULE.SummarizationService
get_summarization_service = MODULE.get_summarization_service


def test_get_summarization_service_returns_singleton():
    first = get_summarization_service()
    second = get_summarization_service()

    assert first is second


def test_summarize_text_fallback_returns_first_three_sentences():
    service = SummarizationService()
    service.available = False
    service.pipeline = None

    text = "One. Two. Three. Four. Five."
    summary = service.summarize_text(text)

    assert summary == "One. Two. Three."


def test_summarize_articles_schema_and_counts_with_mixed_inputs():
    service = SummarizationService()
    service.available = False
    service.pipeline = None

    articles = [
        {
            "title": "Too short",
            "full_text": "Short text",
            "source": "SourceA",
            "url": "https://a.example",
        },
        {
            "title": "Long enough",
            "full_text": "Word " * 120 + ". Second sentence. Third sentence. Fourth sentence.",
            "source": "SourceB",
            "url": "https://b.example",
        },
        {
            "title": "Missing full text",
            "full_text": None,
            "source": "SourceC",
            "url": "https://c.example",
        },
    ]

    result = service.summarize_articles(articles)

    assert set(result.keys()) == {
        "overall_summary",
        "articles",
        "article_count",
        "summarized_count",
    }
    assert result["article_count"] == 3
    assert result["summarized_count"] == 1
    assert len(result["articles"]) == 3

    first = result["articles"][0]
    assert first["title"] == "Too short"
    assert first["source"] == "SourceA"
    assert first["url"] == "https://a.example"
    assert first["summary"] is None
    assert first["scraped"] is False

    second = result["articles"][1]
    assert second["summary"] is not None
    assert second["scraped"] is True


def test_summarize_articles_zero_scrape_uses_required_fallback_message():
    service = SummarizationService()
    service.available = False
    service.pipeline = None

    articles = [
        {
            "title": "A",
            "full_text": None,
            "source": "S1",
            "url": "U1",
        },
        {
            "title": "B",
            "full_text": "tiny",
            "source": "S2",
            "url": "U2",
        },
    ]

    result = service.summarize_articles(articles)

    assert result["summarized_count"] == 0
    assert result["overall_summary"] == FALLBACK_OVERALL_SUMMARY


def test_summarize_text_handles_long_input_with_chunking_path_when_pipeline_available():
    service = SummarizationService()

    class FakePipeline:
        def __call__(self, text, max_length, min_length, do_sample):
            assert max_length == 130
            assert min_length == 30
            assert do_sample is False
            return [{"summary_text": text[:50]}]

    service.available = True
    service.pipeline = FakePipeline()

    long_text = "word " * 1000
    summary = service.summarize_text(long_text)

    assert isinstance(summary, str)
    assert summary.strip() != ""
