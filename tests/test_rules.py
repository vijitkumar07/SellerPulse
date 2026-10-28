from datetime import date
import pytest
from backend.app.rules import payout_is_eligible, calculate_commission, calculate_net

def test_hold_window():
    assert not payout_is_eligible(None, date(2026, 4, 30), 7)
    assert not payout_is_eligible(date(2026, 4, 1), date(2026, 4, 7), 7)
    assert payout_is_eligible(date(2026, 4, 1), date(2026, 4, 8), 7)

def test_commission_10_percent():
    assert calculate_commission(200_000, 1000) == 20_000

def test_net():
    assert calculate_net(200_000, 20_000, 10_000, 5_000) == 165_000

def test_invalid_deductions():
    with pytest.raises(ValueError):
        calculate_net(100, 80, 30, 0)
