from datetime import date
import pytest
from backend.app.rules import (
    payout_is_eligible,
    calculate_commission,
    calculate_net,
)
def test_refund_reserve_and_dispute_all_reconciled():
    # Values are in paise: ₹100 gross - ₹10 commission - ₹5 dispute
    # - ₹3 reserve - ₹2 refund = ₹80 net.
    assert calculate_net(
        gross_paise=10_000,
        commission_paise=1_000,
        dispute_paise=500,
        reserve_paise=300,
        refund_paise=200,
    ) == 8_000
def test_no_deductions_returns_gross_less_commission():
    assert calculate_net(10_000, 1_000, 0, 0) == 9_000
def test_refund_cannot_make_net_negative():
    with pytest.raises(ValueError, match="Deductions cannot exceed gross"):
        calculate_net(1_000, 100, 100, 100, 800)
def test_negative_refund_is_rejected():
    with pytest.raises(ValueError, match="Amounts must be nonnegative"):
        calculate_net(1_000, 100, 0, 0, -1)
def test_commission_is_applied_once_at_expected_rate():
    commission = calculate_commission(10_000, 1_000)
    assert commission == 1_000
    assert calculate_net(10_000, commission, 0, 0) == 9_000
def test_payout_header_matches_sum_of_lines():
    line_net_amounts = [8_000, 9_000, 7_500]
    payout_header_total = sum(line_net_amounts)
    assert payout_header_total == 24_500
def test_hold_release_boundary():
    delivered = date(2026, 4, 1)
    assert not payout_is_eligible(delivered, date(2026, 4, 7), 7)
    assert payout_is_eligible(delivered, date(2026, 4, 8), 7)
def test_negative_hold_window_is_rejected():
    with pytest.raises(ValueError, match="Hold days must be nonnegative"):
        payout_is_eligible(date(2026, 4, 1), date(2026, 4, 2), -1)
