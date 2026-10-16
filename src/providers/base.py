"""Agency and bank evidence provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class AgencyStatus:
    status: str  # CLAIM_RECEIVED | PROCESSING | APPROVED | PAYMENT_ISSUED | REJECTED | NEEDS_DOCS
    reference: str | None
    checked_at: datetime
    raw: dict | None = None


@dataclass
class BankTransaction:
    amount_cents: int
    posted_at: datetime
    description: str
    reference: str | None
    account_mask: str
    synthetic: bool = True


@dataclass
class BankMatch:
    confidence: str  # HIGH | MEDIUM | LOW
    transaction: BankTransaction
    reasons: list[str]


class AgencyStatusProvider(Protocol):
    def get_status(self, confirmation_id: str) -> AgencyStatus: ...


class BankTransactionProvider(Protocol):
    def list_recent(self, account_id: str) -> list[BankTransaction]: ...

    def match_payment(
        self,
        account_id: str,
        *,
        amount_cents: int,
        issued_at: datetime | None,
        reference: str | None,
    ) -> BankMatch | None: ...
