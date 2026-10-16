"""Read-only Gmail API calls for one connected account."""

from collections.abc import Iterator

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .parse import EmailMessage, parse_message

# Skips marketing and social mail. Invoices, payroll, vendor and agency mail is what shows
# what a business actually does.
DEFAULT_QUERY = "newer_than:1y -category:promotions -category:social"

PAGE_SIZE = 100  # messages.list allows up to 500
RETRIES = 3  # retried with backoff on 429 and 5xx


class GmailClient:
    def __init__(self, credentials: Credentials):
        self._users = build("gmail", "v1", credentials=credentials, cache_discovery=False).users()

    def profile(self) -> dict:
        """The account's emailAddress, messagesTotal and threadsTotal."""
        return self._users.getProfile(userId="me").execute(num_retries=RETRIES)

    def search(self, query: str, limit: int) -> Iterator[EmailMessage]:
        """Yield up to `limit` messages matching a query, newest first.

        `query` uses Gmail search-box syntax, e.g. "from:gusto.com newer_than:1y".
        """
        for message_id in self.search_ids(query, limit):
            yield self.get(message_id)

    def search_ids(self, query: str, limit: int) -> Iterator[str]:
        page_token = None
        remaining = limit
        while remaining > 0:
            page = (
                self._users.messages()
                .list(userId="me", q=query, maxResults=min(PAGE_SIZE, remaining), pageToken=page_token)
                .execute(num_retries=RETRIES)
            )
            refs = page.get("messages", [])
            for ref in refs:
                yield ref["id"]
            remaining -= len(refs)
            page_token = page.get("nextPageToken")
            if not page_token:
                return

    def get(self, message_id: str) -> EmailMessage:
        raw = self._users.messages().get(userId="me", id=message_id, format="full").execute(num_retries=RETRIES)
        return parse_message(raw)
