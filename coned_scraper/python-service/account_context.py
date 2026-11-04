"""
Current Con Edison account for the running request or background job.

One ConEd login can hold several accounts. Rows in the per-account tables
(bills, payments, balance history, scraped data, realtime readings) carry an
account_id, and db.py filters every query on the account set here.

The account that existed before multi-account support is "primary", so data
saved by older versions keeps working without a migration.
"""
from __future__ import annotations

import contextvars
import re
from contextlib import contextmanager
from typing import Iterator, Optional

PRIMARY_ACCOUNT = "primary"

_current_account: contextvars.ContextVar[str] = contextvars.ContextVar(
    "coned_current_account", default=PRIMARY_ACCOUNT
)


def current_account() -> str:
    """Account key for the running request or job."""
    return _current_account.get()


def is_primary(account_key: Optional[str] = None) -> bool:
    key = current_account() if account_key is None else account_key
    return key == PRIMARY_ACCOUNT


def set_account(account_key: str) -> contextvars.Token:
    """Set the account for the rest of this task. Return a token for reset_account."""
    return _current_account.set(normalize_account_key(account_key))


def reset_account(token: contextvars.Token) -> None:
    _current_account.reset(token)


@contextmanager
def use_account(account_key: str) -> Iterator[str]:
    """Run a block of code for one account."""
    token = set_account(account_key)
    try:
        yield current_account()
    finally:
        reset_account(token)


def account_digits(value: Optional[str]) -> str:
    """Digits of a ConEd account number, e.g. '12-3456-7890-1234-5' -> '123456789012345'."""
    return re.sub(r"\D", "", value or "")


def normalize_account_key(value: Optional[str]) -> str:
    """Account keys are 'primary' or the account number's digits."""
    if not value:
        return PRIMARY_ACCOUNT
    value = str(value).strip()
    if value.lower() == PRIMARY_ACCOUNT:
        return PRIMARY_ACCOUNT
    digits = account_digits(value)
    return digits or PRIMARY_ACCOUNT


# Labels of known accounts, refreshed by db.get_accounts(). Used to name the
# account in notifications and TTS without a database call.
_account_labels: dict = {}


def remember_account_labels(accounts) -> None:
    global _account_labels
    _account_labels = {a["key"]: (a.get("label") or a["key"]) for a in accounts if a.get("key")}


def has_multiple_accounts() -> bool:
    return len(_account_labels) > 1


def current_account_label() -> Optional[str]:
    """Label of the current account, or None when there is only one account."""
    if not has_multiple_accounts():
        return None
    return _account_labels.get(current_account())


def scoped_name(base: str, account_key: Optional[str] = None) -> str:
    """Per-account name for a setting key or file. The primary account keeps the bare name."""
    key = current_account() if account_key is None else account_key
    if key == PRIMARY_ACCOUNT:
        return base
    return f"{base}@{key}"
