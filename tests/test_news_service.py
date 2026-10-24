from services import news_service


def test_get_company_news_falls_back_to_yahoo_search(monkeypatch):
    ticker_news = []
    search_news = [
        {
            "content": {
                "title": "Reliance update",
                "provider": {"displayName": "Example News"},
                "canonicalUrl": {"url": "https://example.com/reliance"},
                "pubDate": "2026-10-07T10:00:00Z",
                "summary": "Example summary",
            }
        }
    ]

    class FakeTicker:
        news = ticker_news

    class FakeSearch:
        news = search_news

    monkeypatch.setattr(news_service.yf, "Ticker", lambda symbol: FakeTicker())
    monkeypatch.setattr(
        news_service.yf,
        "Search",
        lambda symbol, max_results, news_count: FakeSearch(),
    )

    result = news_service.get_company_news("RELIANCE")

    assert result == [
        {
            "title": "Reliance update",
            "publisher": "Example News",
            "link": "https://example.com/reliance",
            "published": "2026-10-07T10:00:00Z",
            "summary": "Example summary",
        }
    ]


def test_get_company_news_does_not_call_search_when_ticker_news_exists(monkeypatch):
    ticker_news = [
        {
            "content": {
                "title": "Existing article",
                "provider": {"displayName": "Example News"},
                "canonicalUrl": {"url": "https://example.com/existing"},
            }
        }
    ]

    class FakeTicker:
        news = ticker_news

    def fail_search(*args, **kwargs):
        raise AssertionError("Search fallback should not run when ticker news exists")

    monkeypatch.setattr(news_service.yf, "Ticker", lambda symbol: FakeTicker())
    monkeypatch.setattr(news_service.yf, "Search", fail_search)

    result = news_service.get_company_news("RELIANCE")

    assert result[0]["title"] == "Existing article"
