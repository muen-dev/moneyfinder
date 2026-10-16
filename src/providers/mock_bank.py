"""Synthetic bank ledger for PAYMENT_CONFIRMED demos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import BankMatch, BankTransaction


class MockBankTransactionProvider:
    def __init__(self) -> None:
        self._txns: dict[str, list[BankTransaction]] = {}

    def emit_deposit(
        self,
        account_id: str,
        *,
        amount_cents: int,
        reference: str | None,
        description: str = "NY OSC UNCLAIMED FUNDS (DEMO)",
    ) -> BankTransaction:
        txn = BankTransaction(
            amount_cents=amount_cents,
            posted_at=datetime.now(timezone.utc),
            description=description,
            reference=reference,
            account_mask="••4821",
            synthetic=True,
        )
        self._txns.setdefault(account_id, []).append(txn)
        return txn

    def list_recent(self, account_id: str) -> list[BankTransaction]:
        return list(self._txns.get(account_id, []))

    def match_payment(
        self,
        account_id: str,
        *,
        amount_cents: int,
        issued_at: datetime | None,
        reference: str | None,
    ) -> BankMatch | None:
        window_start = (issued_at or datetime.now(timezone.utc)) - timedelta(days=1)
        window_end = (issued_at or datetime.now(timezone.utc)) + timedelta(days=45)
        for txn in self.list_recent(account_id):
            if txn.amount_cents != amount_cents:
                continue
            if not (window_start <= txn.posted_at <= window_end):
                continue
            reasons = ["Amount match", "Date window match"]
            conf = "MEDIUM"
            if reference and txn.reference and reference == txn.reference:
                reasons.append("Reference match")
                conf = "HIGH"
            elif "UNCLAIMED" in txn.description.upper():
                reasons.append("Description suggests NY unclaimed funds")
                conf = "MEDIUM"
            return BankMatch(confidence=conf, transaction=txn, reasons=reasons)
        return None
