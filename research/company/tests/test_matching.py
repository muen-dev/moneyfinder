"""Generic company names ("Main Capital") must not pull in unrelated search results."""

from company_research.collectors import Context, bbb, mentions, news


class SearchOnly:
    def __init__(self, hits):
        self.hits = hits

    def search(self, query, include_domains=None, max_results=5, **kw):
        return self.hits, "tavily"


def hit(url, title, content=""):
    return {"url": url, "title": title, "content": content}


def test_mentions_needs_the_name_as_written():
    names = ["Main Capital"]
    assert mentions("Main Capital closes a new credit line", names, "themaincapital.com")
    assert mentions("see themaincapital.com", names, "themaincapital.com")
    assert not mentions("easy access from the main capital", names, "themaincapital.com")
    assert not mentions("Main Capitalization rules", names, "themaincapital.com")


def test_news_needs_a_new_york_tie_without_the_domain():
    hits = [
        hit("https://example.org/foxway", "Foxway, a company of Main Capital", "Main Capital invests in Amsterdam"),
        hit("https://example.org/tour", "Cotopaxi Day Tour", "easy access from the main capital"),
        hit("https://example.org/nyc", "Main Capital opens Brooklyn office", "Main Capital is hiring in New York"),
    ]
    ctx = Context("themaincapital.com", SearchOnly(hits), names=["Main Capital"])
    urls = {f.source.url for f in news.collect(ctx).facts}
    assert urls == {"https://example.org/nyc"}


def test_bbb_skips_profiles_of_other_businesses():
    hits = [
        hit("https://www.bbb.org/us/ny/new-york/profile/financial-services/capital-group-0121-102358", "Capital Group | BBB Business Profile"),
        hit("https://www.bbb.org/us/ny/new-york/profile/loans/american-capital-group-0121-129833", "American Capital Group | BBB"),
    ]
    ctx = Context("themaincapital.com", SearchOnly(hits), names=["Main Capital"])
    assert bbb.best_profile(hits, ctx) == (None, {})

    own = hit("https://www.bbb.org/us/ny/new-york/profile/loans/main-capital-llc-0121-1", "Main Capital LLC | BBB")
    assert bbb.best_profile(hits + [own], ctx)[0] == own["url"]
