import pytest

from company_research.domain import InvalidDomain, from_email, normalize


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("joespizza.com", "joespizza.com"),
        ("https://WWW.JoesPizza.com/menu?x=1#top", "joespizza.com"),
        ("shop.joespizza.com.", "joespizza.com"),
        ("owner@joespizza.com", "joespizza.com"),
        ("joespizza.co.uk", "joespizza.co.uk"),
        ("bücher.de", "xn--bcher-kva.de"),
    ],
)
def test_normalizes(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "localhost", "127.0.0.1", "127.1", "[::1]", "http://10.0.0.1/", "joespizza.com:8080", "printer.local",
     "db.internal", "co.uk", "com", "ftp://joespizza.com", "http://user:pw@joespizza.com", "not a domain", "x" * 400],
)
def test_rejects(raw):
    with pytest.raises(InvalidDomain):
        normalize(raw)


def test_email_prefill_skips_free_providers():
    assert from_email("owner@JoesPizza.com") == "joespizza.com"
    assert from_email("owner@gmail.com") is None
    assert from_email("owner@hotmail.co.uk") is None
