import base64

import pytest

from business_research import ids
from business_research.gmail.parse import parse_message


def b64(text: str, encoding: str = "utf-8") -> str:
    return base64.urlsafe_b64encode(text.encode(encoding)).decode().rstrip("=")


def part(mime: str, text: str = "", filename: str = "", charset: str = "utf-8", parts=None) -> dict:
    p = {
        "mimeType": mime,
        "filename": filename,
        "headers": [{"name": "Content-Type", "value": f"{mime}; charset={charset}"}],
        "body": {"data": b64(text, charset)} if text else {},
    }
    if parts:
        p["parts"] = parts
    return p


def message(payload: dict) -> dict:
    payload["headers"] = payload.get("headers", []) + [
        {"name": "From", "value": "Gusto <no-reply@Gusto.com>"},
        {"name": "To", "value": "owner@joespizza.com"},
        {"name": "Subject", "value": "Payroll processed"},
    ]
    return {
        "id": "m1",
        "threadId": "t1",
        "internalDate": "1760000000000",
        "labelIds": ["INBOX"],
        "snippet": "Your payroll",
        "payload": payload,
    }


def test_prefers_plain_text_and_lists_attachments():
    raw = message(
        part(
            "multipart/mixed",
            parts=[
                part(
                    "multipart/alternative",
                    parts=[part("text/plain", "Payroll for 12 employees"), part("text/html", "<p>ignored</p>")],
                ),
                part("application/pdf", filename="invoice-0042.pdf"),
            ],
        )
    )
    msg = parse_message(raw)
    assert msg.body == "Payroll for 12 employees"
    assert msg.attachments == ["invoice-0042.pdf"]
    assert msg.sender_domain == "gusto.com"
    assert msg.subject == "Payroll processed"
    assert msg.date == "2025-10-09T08:53:20+00:00"


def test_falls_back_to_html_text():
    html = "<html><head><style>p{}</style></head><body><p>Tax &amp; payroll</p><script>x()</script></body></html>"
    msg = parse_message(message(part("text/html", html)))
    assert msg.body == "Tax & payroll"


def test_decodes_declared_charset():
    msg = parse_message(message(part("text/plain", "Café receipt", charset="iso-8859-1")))
    assert msg.body == "Café receipt"


@pytest.mark.parametrize("bad", ["../etc", "Joes Pizza", "", "a/b", "joes\n"])
def test_rejects_unsafe_business_ids(bad):
    with pytest.raises(ValueError):
        ids.check(bad)


def test_business_id_from_email():
    assert ids.from_email("Owner@JoesPizza.com") == "owner-joespizza-com"
    long_id = ids.from_email("a" * 80 + "@example.com")
    assert len(long_id) == 64 and ids.check(long_id)
