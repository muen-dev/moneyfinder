"""Google OAuth (web server flow) for a business's Gmail account, with one stored token per business."""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError
from oauthlib.oauth2 import OAuth2Error

from .. import config, ids
from .client import GmailClient

# Read-only: we only look at mail, never send, label, or delete it.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class NotConnectedError(RuntimeError):
    """The business has no usable Gmail token; it has to sign in again."""


class LoginError(RuntimeError):
    """Google sign-in finished without usable Gmail access."""


@dataclass
class Connection:
    business_id: str
    email: str
    connected_at: str
    credentials: Credentials


@dataclass
class PendingLogin:
    auth_url: str
    state: str
    code_verifier: str


def start_login(redirect_uri: str) -> PendingLogin:
    """Build Google's consent URL. Keep `state` and `code_verifier` for `finish_login`."""
    flow = _flow(redirect_uri)
    # prompt=consent makes Google issue a refresh token even if this account consented before.
    auth_url, state = flow.authorization_url(prompt="consent")
    return PendingLogin(auth_url, state, flow.code_verifier)


def finish_login(redirect_uri: str, code: str, code_verifier: str) -> Connection:
    """Exchange the code from Google's redirect for a token and store it.

    The caller must already have matched the redirect's `state` to the one from `start_login`.
    """
    flow = _flow(redirect_uri, code_verifier=code_verifier)
    try:
        flow.fetch_token(code=code)
        email = GmailClient(flow.credentials).profile()["emailAddress"]
    except Warning as e:
        # oauthlib raises this when Google grants other scopes than requested,
        # e.g. the user left the Gmail checkbox unticked on the consent screen.
        raise LoginError("Gmail read access wasn't granted. Sign in again and allow it.") from e
    except OAuth2Error as e:
        raise LoginError(f"Google rejected the sign-in: {e.description or e.error}") from e
    except HttpError as e:
        raise LoginError(f"Signed in, but reading the mailbox failed: {e.reason}") from e

    business_id = ids.from_email(email)
    conn = Connection(business_id, email, datetime.now(UTC).isoformat(timespec="seconds"), flow.credentials)
    _write(_token_path(business_id), conn)
    return conn


def get(business_id: str) -> Connection:
    """The stored connection, without refreshing or contacting Google."""
    return _read(_token_path(business_id))


def load(business_id: str) -> Connection:
    """The stored connection, with its access token refreshed if it has expired."""
    path = _token_path(business_id)
    conn = _read(path)
    if not conn.credentials.valid:
        try:
            conn.credentials.refresh(Request())
        except RefreshError as e:
            # Revoked by the account owner, or expired: apps in "Testing" get 7-day refresh tokens.
            raise NotConnectedError(
                f"Gmail access for {conn.email} is no longer valid ({e}). Sign in with Google again."
            ) from e
        _write(path, conn)
    return conn


def list_connections() -> list[Connection]:
    if not config.TOKEN_DIR.exists():
        return []
    return [_read(path) for path in sorted(config.TOKEN_DIR.glob("*.json"))]


def disconnect(business_id: str) -> bool:
    """Revoke Google access and delete the stored token. Returns whether Google accepted the revoke."""
    path = _token_path(business_id)
    creds = _read(path).credentials
    response = Request()(
        url=REVOKE_URL,
        method="POST",
        body=urlencode({"token": creds.refresh_token or creds.token}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    path.unlink()
    return response.status == 200


def _flow(redirect_uri: str, code_verifier: str | None = None) -> Flow:
    if not config.CLIENT_SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"OAuth client file not found at {config.CLIENT_SECRETS_FILE}; "
            "see research/business/README.md for how to create it"
        )
    return Flow.from_client_secrets_file(
        str(config.CLIENT_SECRETS_FILE), SCOPES, redirect_uri=redirect_uri, code_verifier=code_verifier
    )


def _token_path(business_id: str) -> Path:
    return config.TOKEN_DIR / f"{ids.check(business_id)}.json"


def _read(path: Path) -> Connection:
    if not path.exists():
        raise NotConnectedError(f"{path.stem!r} is not connected. Sign in with Google first.")
    data = json.loads(path.read_text())
    creds = Credentials.from_authorized_user_info(data["credentials"], SCOPES)
    return Connection(path.stem, data["email"], data["connected_at"], creds)


def _write(path: Path, conn: Connection) -> None:
    config.TOKEN_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = {
        "email": conn.email,
        "connected_at": conn.connected_at,
        "credentials": json.loads(conn.credentials.to_json()),
    }
    # The refresh token grants ongoing access to the inbox, so the file is owner-only.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
