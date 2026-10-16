from business_research import inbox


def test_category_matches_domains_subdomains_and_gov():
    assert inbox.category("gusto.com") == "Payroll and HR"
    assert inbox.category("mail.Chase.com") == "Banking and lending"
    assert inbox.category("tax.ny.gov") == "Government"
    assert inbox.category("notgusto.com") is None
    assert inbox.category("") is None


def test_summarize_groups_known_senders():
    messages = [
        {"sender_domain": "gusto.com", "date": "2026-03-01T00:00:00+00:00", "attachments": ["w2.pdf"]},
        {"sender_domain": "gusto.com", "date": "2026-01-15T00:00:00+00:00", "attachments": []},
        {"sender_domain": "tax.ny.gov", "date": "2026-02-01T00:00:00+00:00"},
        {"sender_domain": "friend.example", "date": "2026-02-02T00:00:00+00:00"},
    ]
    summary = inbox.summarize(messages)
    assert (summary["messages"], summary["senders"], summary["attachments"]) == (4, 3, 1)
    assert (summary["first"], summary["last"]) == ("2026-01-15", "2026-03-01")
    assert [c["name"] for c in summary["categories"]] == ["Payroll and HR", "Government"]
    assert summary["categories"][0]["senders"] == [("gusto.com", 2)]
