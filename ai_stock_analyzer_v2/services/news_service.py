import yfinance as yf


def get_company_news(symbol):
    """
    Fetch and normalize company news from Yahoo Finance.

    Returns:
        list of dictionaries containing:
        title
        publisher
        link
        published
        summary
    """

    try:

        symbol = symbol.strip().upper()

        # Add NSE suffix when required
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"

        ticker = yf.Ticker(symbol)

        raw_news = ticker.news or []

        # Yahoo's ticker-news endpoint can occasionally return no articles
        # even when Yahoo Finance search has current news for the symbol.
        if not raw_news:
            try:
                search = yf.Search(symbol, max_results=10, news_count=10)
                raw_news = search.news or []
            except Exception:
                raw_news = []

        normalized_news = []

        for article in raw_news:

            if not isinstance(article, dict):
                continue

            # --------------------------------------------------
            # Newer Yahoo / yfinance structure
            # --------------------------------------------------

            content = article.get("content", {})

            if not isinstance(content, dict):
                content = {}

            # --------------------------------------------------
            # Title
            # --------------------------------------------------

            title = content.get("title") or article.get("title") or "No Title"

            # --------------------------------------------------
            # Publisher / Provider
            # --------------------------------------------------

            provider = content.get("provider", {})

            if isinstance(provider, dict):
                publisher = provider.get("displayName") or provider.get("name")
            else:
                publisher = provider

            publisher = publisher or article.get("publisher") or "Unknown"

            # --------------------------------------------------
            # Link
            # --------------------------------------------------

            canonical_url = content.get("canonicalUrl", {})

            click_through_url = content.get("clickThroughUrl", {})

            link = ""

            if isinstance(canonical_url, dict):
                link = canonical_url.get("url", "")

            elif isinstance(canonical_url, str):
                link = canonical_url

            if not link:

                if isinstance(
                    click_through_url,
                    dict,
                ):
                    link = click_through_url.get("url", "")

                elif isinstance(
                    click_through_url,
                    str,
                ):
                    link = click_through_url

            if not link:
                link = article.get("link", "")

            # --------------------------------------------------
            # Published Date
            # --------------------------------------------------

            published = (
                content.get("pubDate")
                or content.get("displayTime")
                or article.get("providerPublishTime")
                or ""
            )

            # --------------------------------------------------
            # Summary
            # --------------------------------------------------

            summary = content.get("summary") or content.get("description") or ""

            # --------------------------------------------------
            # Ignore completely unusable records
            # --------------------------------------------------

            if title == "No Title" and publisher == "Unknown" and not link:
                continue

            normalized_news.append(
                {
                    "title": str(title),
                    "publisher": str(publisher),
                    "link": str(link) if link else "",
                    "published": published,
                    "summary": str(summary) if summary else "",
                }
            )

        return normalized_news

    except Exception as error:

        print(f"News Error: {error}")

        return []
