
from collections import defaultdict

from sqlalchemy.orm import Session

from .models import (
    Seller,
    ProductListing,
    Order,
    Fulfillment,
    Dispute,
    Payout,
    PayoutLine,
    CommissionRule,
)


def detect_anomalies(db: Session) -> list[dict]:
    findings = []
    seen = set()

    def add_finding(scenario, record_id, severity, details):
        key = (scenario, record_id)
        if key in seen:
            return
        seen.add(key)
        findings.append(
            {
                "scenario": scenario,
                "record_id": record_id,
                "severity": severity,
                "details": details,
            }
        )

    # Effective active default commission rule.
    active_rule = (
        db.query(CommissionRule)
        .filter(
            CommissionRule.is_active.is_(True),
            CommissionRule.seller_id.is_(None),
        )
        .order_by(CommissionRule.id)
        .first()
    )
    commission_rate = active_rule.rate if active_rule else 0.10

    payouts = db.query(Payout).all()
    lines = db.query(PayoutLine).all()
    fulfillments = db.query(Fulfillment).all()

    lines_by_payout = defaultdict(list)
    lines_by_order = defaultdict(list)
    fulfillments_by_order = defaultdict(list)

    for line in lines:
        lines_by_payout[line.payout_id].append(line)
        lines_by_order[line.order_id].append(line)

    for fulfillment in fulfillments:
        fulfillments_by_order[fulfillment.order_id].append(fulfillment)

    # 1. Active listing owned by a suspended seller.
    rows = (
        db.query(ProductListing, Seller)
        .join(Seller, ProductListing.seller_id == Seller.id)
        .filter(
            Seller.status == "suspended",
            ProductListing.status == "active",
        )
        .all()
    )

    for listing, seller in rows:
        add_finding(
            "suspended_seller_listing_active",
            listing.id,
            "high",
            f"Listing {listing.id} is active while seller {seller.id} "
            "is suspended.",
        )

    # 2. Payout made before all relevant fulfillments are delivered,
    # or before the payout hold has been released.
    for payout in payouts:
        if payout.status != "paid":
            continue

        payout_lines = lines_by_payout.get(payout.id, [])
        if not payout_lines:
            continue

        premature = (
            payout.hold_released_at is None
            or payout.created_at < payout.hold_released_at
        )

        relevant_fulfillments = []
        for line in payout_lines:
            relevant_fulfillments.extend(
                fulfillments_by_order.get(line.order_id, [])
            )

        if not relevant_fulfillments:
            premature = True
        elif any(
            item.delivered_at is None
            or payout.created_at < item.delivered_at
            for item in relevant_fulfillments
        ):
            premature = True

        if premature:
            add_finding(
                "payout_before_delivery_or_hold_release",
                payout.id,
                "high",
                f"Payout {payout.id} was made before delivery "
                "or hold release.",
            )

    # 3. Payout total must equal the sum of payout-line net amounts.
    for payout in payouts:
        payout_lines = lines_by_payout.get(payout.id, [])
        if not payout_lines:
            continue

        line_total = round(sum(line.net_amount for line in payout_lines), 2)
        if abs(round(payout.total_amount - line_total, 2)) > 0.01:
            add_finding(
                "payout_total_mismatch",
                payout.id,
                "high",
                f"Payout total {payout.total_amount:.2f} differs "
                f"from line total {line_total:.2f}.",
            )

    # 4. Commission applied twice or above the expected default rate.
    for line in lines:
        expected = round(line.gross_amount * commission_rate, 2)

        if line.commission_amount > expected + 0.01:
            add_finding(
                "commission_applied_twice",
                line.payout_id,
                "medium",
                f"Commission {line.commission_amount:.2f} exceeds "
                f"the expected commission {expected:.2f}.",
            )

    # 5. Resolved disputes must be reflected in payout deductions.
    resolved_disputes = (
        db.query(Dispute)
        .filter(Dispute.status == "resolved")
        .all()
    )

    for dispute in resolved_disputes:
        order_lines = lines_by_order.get(dispute.order_id, [])
        if not order_lines:
            continue

        for line in order_lines:
            if line.dispute_deduction + 0.01 < dispute.amount:
                add_finding(
                    "dispute_not_deducted",
                    line.payout_id,
                    "medium",
                    f"Payout line {line.id} has dispute deduction "
                    f"{line.dispute_deduction:.2f}, below dispute "
                    f"amount {dispute.amount:.2f}.",
                )

    return findings
