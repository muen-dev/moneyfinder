"""Business ids: filesystem-safe slugs that name a business's token and data files."""

import hashlib
import re

_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def check(business_id: str) -> str:
    """Return the id unchanged, or raise ValueError if it isn't safe to use as a filename."""
    if not _PATTERN.fullmatch(business_id):
        raise ValueError(
            f"business id must be lowercase letters, digits, '-' or '_' (e.g. joes-pizza), got {business_id!r}"
        )
    return business_id


def from_email(email: str) -> str:
    """Stable id for a Google account, e.g. owner@joespizza.com -> owner-joespizza-com."""
    slug = re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")
    if len(slug) > 64:
        slug = f"{slug[:55]}-{hashlib.sha256(email.lower().encode()).hexdigest()[:8]}"
    return slug
