from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SERVICE_FILE = Path(__file__).resolve().parents[1] / "app" / "services" / "news_service.py"
SPEC = spec_from_file_location("news_service", SERVICE_FILE)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_extract_article_paragraphs_from_article_url():
    article_url = "https://economictimes.indiatimes.com/markets/stocks/news/vedantas-65-share-price-crash-an-illusion-the-stock-is-down-just-5-heres-why/articleshow/130623628.cms?from=mdr"

    paragraphs = MODULE.extract_article_paragraphs(article_url)

    print("\nExtracted paragraphs:\n")
    for index, paragraph in enumerate(paragraphs, start=1):
        print(f"{index}. {paragraph}")

    assert isinstance(paragraphs, list)
    assert len(paragraphs) > 0, "No paragraphs were extracted"