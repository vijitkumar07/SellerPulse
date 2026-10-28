from datetime import date, timedelta
def payout_is_eligible(delivered_on: date | None, payout_on: date, hold_days: int) -> bool:
    if delivered_on is None:
        return False
    if hold_days < 0:
        raise ValueError("Hold days must be nonnegative")
    return payout_on >= delivered_on + timedelta(days=hold_days)
def calculate_commission(gross_paise: int, rate_bps: int) -> int:
    if gross_paise < 0 or not 0 <= rate_bps <= 10_000:
        raise ValueError("Invalid gross amount or commission rate")
    return (gross_paise * rate_bps + 5_000) // 10_000
def calculate_net(
    gross_paise: int,
    commission_paise: int,
    dispute_paise: int,
    reserve_paise: int,
    refund_paise: int = 0,
) -> int:
    values = (
        gross_paise,
        commission_paise,
        dispute_paise,
        reserve_paise,
        refund_paise,
    )
    if any(v < 0 for v in values):
        raise ValueError("Amounts must be nonnegative")
    if sum(values[1:]) > gross_paise:
        raise ValueError("Deductions cannot exceed gross")
    return gross_paise - sum(values[1:])
