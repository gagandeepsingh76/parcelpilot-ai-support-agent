"""Username/password authentication for both caller kinds.

Complements the mock session registry (kept for the demo UI and tests) with
real credential auth:

- customers sign in with username + password and are bound to their account
- internal staff sign in with username + password and carry their RBAC role

Design notes
------------
- Passwords: PBKDF2-HMAC-SHA256, 200k iterations, per-user 16-byte salt.
  Stdlib only - no new dependency for a demo-grade auth layer.
- Tokens: stateless HMAC-signed (base64url(payload).base64url(signature)).
  No server-side session store needed; survives ephemeral-disk reboots on
  Render. Signature secret comes from AUTH_SECRET in settings.
- Seeded demo users mirror MOCK_SESSIONS so either login path yields the
  same access-control identity (same scopes, same enforcement code paths).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
import time
from typing import Any

from app.access import AccessDeniedError, Caller
from app.config import get_settings

_PBKDF2_ITERATIONS = 200_000
_TOKEN_TTL_SECONDS = 7 * 24 * 3600

# username -> (password, kind, role, account_id, display_name)
DEMO_USERS: dict[str, tuple[str, str, str | None, str | None, str]] = {
    "northstar": ("demo1234", "customer", None, "ACC-001", "Northstar Logistics portal"),
    "lumenworks": ("demo1234", "customer", None, "ACC-002", "LumenWorks Ltd portal"),
    "brightcart": ("demo1234", "customer", None, "ACC-003", "BrightCart Commerce portal"),
    "agent": ("staff1234", "internal", "support_agent", None, "Avery (support agent)"),
    "ops": ("staff1234", "internal", "ops", None, "Priya (ops)"),
    "admin": ("staff1234", "internal", "admin", None, "Root (admin)"),
    "viewer": ("staff1234", "internal", "viewer", None, "Intern (viewer)"),
}


# --------------------------------------------------------------------------
# password hashing
# --------------------------------------------------------------------------
def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)


def hash_password(password: str) -> tuple[bytes, bytes]:
    salt = hashlib.sha256(str(time.time_ns()).encode() + b"parcelpilot").digest()[:16]
    return salt, _hash_password(password, salt)


def verify_password(password: str, salt: bytes, expected_hash: bytes) -> bool:
    return hmac.compare_digest(_hash_password(password, salt), expected_hash)


# --------------------------------------------------------------------------
# signed stateless tokens
# --------------------------------------------------------------------------
def _secret() -> bytes:
    return get_settings().auth_secret.encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(caller: Caller) -> str:
    payload = {
        "sub": caller.session_id.removeprefix("user:"),
        "kind": caller.kind,
        "role": caller.role,
        "account_id": caller.account_id,
        "display_name": caller.display_name,
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }
    body = _b64url(json.dumps(payload).encode())
    sig = _b64url(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"ppat.{body}.{sig}"  # ppat = ParcelPilot Auth Token


def resolve_signed_token(authorization_header: str | None) -> Caller | None:
    """Return a Caller for our signed tokens, or None if not one of ours.

    Raising is reserved for tokens that LOOK like ours but fail validation -
    anything else falls back to the mock registry unchanged.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None
    token = authorization_header.removeprefix("Bearer ").strip()
    if not token.startswith("ppat."):
        return None
    try:
        _, body, sig = token.split(".")
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig)):
            raise AccessDeniedError("invalid or expired session token")
        payload = json.loads(_b64url_decode(body))
        if int(payload.get("exp", 0)) < time.time():
            raise AccessDeniedError("invalid or expired session token")
    except (ValueError, json.JSONDecodeError) as exc:
        raise AccessDeniedError("invalid or expired session token") from exc

    kind = payload["kind"]
    if kind == "customer":
        spec = {"kind": kind, "account_id": payload.get("account_id"),
                "display_name": payload.get("display_name") or "customer"}
    else:
        spec = {"kind": kind, "role": payload.get("role"),
                "display_name": payload.get("display_name") or "staff"}
    return Caller(session_id=token, **spec)


# --------------------------------------------------------------------------
# database plumbing
# --------------------------------------------------------------------------
def ensure_auth_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_users (
            username      TEXT PRIMARY KEY,
            password_salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            kind          TEXT NOT NULL CHECK (kind IN ('customer', 'internal')),
            role          TEXT,
            account_id    TEXT,
            display_name  TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def seed_default_users(conn: sqlite3.Connection) -> None:
    """Idempotently insert the demo credentials (never overwrites changes)."""
    existing = {r["username"] for r in conn.execute("SELECT username FROM app_users")}
    for username, (password, kind, role, account_id, display_name) in DEMO_USERS.items():
        if username in existing:
            continue
        salt, digest = hash_password(password)
        conn.execute(
            "INSERT INTO app_users (username, password_salt, password_hash, kind,"
            " role, account_id, display_name) VALUES (?,?,?,?,?,?,?)",
            (username, salt, digest, kind, role, account_id, display_name),
        )
    conn.commit()


from pathlib import Path


def bootstrap_auth(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_auth_tables(conn)
        seed_default_users(conn)
    finally:
        conn.close()


# --------------------------------------------------------------------------
# credential flows
# --------------------------------------------------------------------------
def authenticate(conn: sqlite3.Connection, username: str, password: str) -> Caller:
    row = conn.execute(
        "SELECT * FROM app_users WHERE username=?", ((username or "").strip(),)
    ).fetchone()
    if row is None or not verify_password(
        password or "", row["password_salt"], row["password_hash"]
    ):
        # same message for unknown user and wrong password (no user enumeration)
        raise AccessDeniedError("invalid username or password")

    common = dict(display_name=row["display_name"], session_id=f"user:{row['username']}")
    if row["kind"] == "customer":
        return Caller(kind="customer", account_id=row["account_id"], **common)
    return Caller(kind="internal", role=row["role"], **common)


def register_customer(
    conn: sqlite3.Connection, username: str, password: str, account_id: str, display_name: str | None = None
) -> Caller:
    """Self-registration creates CUSTOMER logins bound to an EXISTING account.

    Staff accounts are provisioned out-of-band only (no self-service signup),
    matching how a real support org would control internal access.
    """
    username = (username or "").strip().lower()
    if len(username) < 3 or not all(c.isalnum() or c in "-_" for c in username):
        raise ValueError("username must be 3+ chars (letters, digits, '-', '_')")
    if len(password or "") < 8:
        raise ValueError("password must be at least 8 characters")
    exists = conn.execute(
        "SELECT 1 FROM accounts WHERE account_id=?", (account_id,)
    ).fetchone()
    if exists is None:
        raise LookupError(f"unknown account '{account_id}'")
    dup = conn.execute("SELECT 1 FROM app_users WHERE username=?", (username,)).fetchone()
    if dup is not None:
        raise FileExistsError(f"username '{username}' is already taken")

    name = display_name or f"{username} portal"
    salt, digest = hash_password(password)
    conn.execute(
        "INSERT INTO app_users (username, password_salt, password_hash, kind,"
        " role, account_id, display_name) VALUES (?,?,?,?,?,?,?)",
        (username, salt, digest, "customer", None, account_id, name),
    )
    conn.commit()
    return Caller(kind="customer", account_id=account_id, display_name=name,
                  session_id=f"user:{username}")
