"""Multi-account helpers: account context, setting keys, opower meter matching."""
from dataclasses import dataclass
from enum import Enum

from account_context import (
    PRIMARY_ACCOUNT,
    current_account,
    normalize_account_key,
    scoped_name,
    use_account,
)
from meter_service import match_opower_accounts, usage_unit


class _MeterType(Enum):
    ELEC = "ELEC"
    GAS = "GAS"

    def __str__(self):
        return self.value


@dataclass
class _Meter:
    uuid: str
    utility_account_id: str
    meter_type: _MeterType


def test_default_account_is_primary():
    assert current_account() == PRIMARY_ACCOUNT


def test_use_account_restores_previous():
    with use_account("0051-2345"):
        assert current_account() == "00512345"
        with use_account("primary"):
            assert current_account() == PRIMARY_ACCOUNT
        assert current_account() == "00512345"
    assert current_account() == PRIMARY_ACCOUNT


def test_normalize_account_key():
    assert normalize_account_key(None) == PRIMARY_ACCOUNT
    assert normalize_account_key("PRIMARY") == PRIMARY_ACCOUNT
    assert normalize_account_key("12-3456-7890") == "1234567890"
    assert normalize_account_key("no digits") == PRIMARY_ACCOUNT


def test_primary_keeps_unsuffixed_names():
    assert scoped_name("tts_bill_state") == "tts_bill_state"
    with use_account("555"):
        assert scoped_name("tts_bill_state") == "tts_bill_state@555"
        assert scoped_name("account_balance") + ".png" == "account_balance@555.png"


def test_meters_match_by_account_digits():
    meters = [
        _Meter("u1", "111111111111111", _MeterType.GAS),
        _Meter("u2", "222222222222222", _MeterType.GAS),
    ]
    registry = [
        {"key": "primary", "site_id": "222222222222222"},
        {"key": "111111111111111", "site_id": "111111111111111"},
    ]
    result = match_opower_accounts(meters, registry)
    assert result["primary"].uuid == "u2"
    assert result["111111111111111"].uuid == "u1"


def test_unmatched_meters_fill_in_order_primary_first():
    meters = [
        _Meter("u1", "AAA-1", _MeterType.GAS),
        _Meter("u2", "BBB-2", _MeterType.GAS),
    ]
    registry = [
        {"key": "999", "site_id": "999999999999999"},
        {"key": "primary", "site_id": "888888888888888"},
    ]
    result = match_opower_accounts(meters, registry)
    assert result["primary"].uuid == "u1"
    assert result["999"].uuid == "u2"


def test_electric_meter_wins_on_shared_account():
    meters = [
        _Meter("gas", "123456789", _MeterType.GAS),
        _Meter("elec", "123456789", _MeterType.ELEC),
    ]
    result = match_opower_accounts(meters, [{"key": "primary", "site_id": None}])
    assert result["primary"].uuid == "elec"


def test_single_account_before_registry_uses_first_meter():
    meters = [_Meter("first", "1", _MeterType.ELEC), _Meter("second", "2", _MeterType.GAS)]
    result = match_opower_accounts(meters, [{"key": "primary", "site_id": None, "number": None}])
    assert result["primary"].uuid == "first"


def test_usage_unit():
    assert usage_unit(_Meter("a", "1", _MeterType.GAS)) == "therms"
    assert usage_unit(_Meter("a", "1", _MeterType.ELEC)) == "kWh"
