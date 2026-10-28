"""Read-only payment and payout audit for SellerPulse."""
from collections import defaultdict
from datetime import datetime
from .models import (
    Seller, ProductListing, Order, Fulfillment, Dispute,
    CommissionRule, Payout, PayoutLine,
)
def audit_payments(db):
    findings = []
    def add(rule, record_id, message):
        findings.append({
            "rule": rule,
            "record_id": str(record_id),
            "message": message,
        })
    sellers = {s.id: s for s in db.query(Seller).all()}
    listings = db.query(ProductListing).all()
    orders = {o.id: o for o in db.query(Order).all()}
    fulfillments = db.query(Fulfillment).all()
    disputes = db.query(Dispute).all()
    payouts = {p.id: p for p in db.query(Payout).all()}
    lines = db.query(PayoutLine).all()
    rules = db.query(CommissionRule).all()
    lines_by_payout = defaultdict(list)
    lines_by_order = defaultdict(list)
    fulfillments_by_order = defaultdict(list)
    disputes_by_order = defaultdict(list)
    for line in lines:
        lines_by_payout[line.payout_id].append(line)
        lines_by_order[line.order_id].append(line)
    for fulfillment in fulfillments:
        fulfillments_by_order[fulfillment.order_id].append(fulfillment)
    for dispute in disputes:
        disputes_by_order[dispute.order_id].append(dispute)
    def commission_rate(seller_id, order_date):
        applicable = []
        for rule in rules:
            if not rule.is_active:
                continue
            if rule.seller_id is not None and rule.seller_id != seller_id:
                continue
            if rule.effective_from and order_date < rule.effective_from:
                continue
            if rule.effective_to and order_date > rule.effective_to:
                continue
            applicable.append(rule)
        seller_rules = [r for r in applicable if r.seller_id == seller_id]
        chosen = seller_rules or [r for r in applicable if r.seller_id is None]
        if not chosen:
            return None
        return float(sorted(chosen, key=lambda r: r.effective_from or datetime.min)[-1].rate)
    # A. Suspended sellers must not have active listings.
    for listing in listings:
        seller = sellers.get(listing.seller_id)
        if seller and str(seller.status).lower() == "suspended" and str(listing.status).lower() == "active":
            add(
                "suspended_seller_listing_active",
                listing.id,
                f"Suspended seller {seller.id} has active listing {listing.id}.",
            )
    # B. Paid payouts must not precede delivery or hold release.
    for payout in payouts.values():
        if str(payout.status).lower() not in {"paid", "completed"}:
            continue
        for line in lines_by_payout[payout.id]:
            order = orders.get(line.order_id)
            order_fulfillments = fulfillments_by_order.get(line.order_id, [])
            if not order_fulfillments:
                add(
                    "payout_before_delivery_or_hold_release",
                    payout.id,
                    f"Order {line.order_id} has no fulfillment record.",
                )
                break
            # Every fulfillment for a split order must be delivered.
            not_delivered = [
                f for f in order_fulfillments
                if str(f.status).lower() != "delivered" or f.delivered_at is None
            ]
            delivery_dates = [
                f.delivered_at for f in order_fulfillments
                if f.delivered_at is not None
            ]
            invalid = (
                order is None
                or str(order.status).lower() != "delivered"
                or bool(not_delivered)
                or not delivery_dates
                or payout.created_at < max(delivery_dates)
                or payout.hold_released_at is None
                or payout.created_at < payout.hold_released_at
            )
            if invalid:
                add(
                    "payout_before_delivery_or_hold_release",
                    payout.id,
                    f"Payout for order {line.order_id} is not eligible by delivery/hold timestamps.",
                )
                break
    # C. Reconcile each payout line and flag excess commission.
    for line in lines:
        gross = float(line.gross_amount or 0)
        commission = float(line.commission_amount or 0)
        dispute_deduction = float(line.dispute_deduction or 0)
        refund = float(line.refund_amount or 0)
        reserve = float(line.reserve_amount or 0)
        expected_net = round(
            gross - commission - dispute_deduction - refund - reserve, 2
        )
        if abs(round(float(line.net_amount or 0), 2) - expected_net) > 0.01:
            add(
                "payout_line_net_mismatch",
                line.id,
                f"Expected net {expected_net}; stored net {line.net_amount}.",
            )
        order = orders.get(line.order_id)
        payout = payouts.get(line.payout_id)
        if order and payout:
            rate = commission_rate(payout.seller_id, order.created_at)
            if rate is not None:
                expected_commission = round(gross * rate, 2)
                if commission > expected_commission + 0.01:
                    add(
                        "commission_applied_twice",
                        line.id,
                        f"Commission {commission} exceeds expected {expected_commission} at rate {rate}.",
                    )
    # D. Payout header must equal the sum of its lines.
    for payout in payouts.values():
        expected_total = round(
            sum(float(line.net_amount or 0) for line in lines_by_payout[payout.id]), 2
        )
        if abs(round(float(payout.total_amount or 0), 2) - expected_total) > 0.01:
            add(
                "payout_total_mismatch",
                payout.id,
                f"Header total {payout.total_amount}; line total {expected_total}.",
            )
    # E. Resolved disputes should be deducted from associated payout lines.
    for dispute in disputes:
        if str(dispute.status).lower() != "resolved":
            continue
        related_lines = lines_by_order.get(dispute.order_id, [])
        if not related_lines:
            continue
        # Only compare against payouts for the same seller as the dispute's order.
        order = orders.get(dispute.order_id)
        relevant_lines = [
            line for line in related_lines
            if order is None
            or payouts.get(line.payout_id) is None
            or payouts[line.payout_id].seller_id == order.seller_id
        ]
        total_deducted = sum(
            float(line.dispute_deduction or 0) for line in relevant_lines
        )
        if total_deducted + 0.01 < float(dispute.amount or 0):
            add(
                "dispute_deduction_missing",
                dispute.id,
                f"Dispute amount {dispute.amount}; recorded deduction {total_deducted}.",
            )
    return findings
def print_payment_audit(db):
    findings = audit_payments(db)
    print(f"Payment audit findings: {len(findings)}")
    for item in findings:
        print(
            f"[{item['rule']}] record={item['record_id']}: "
            f"{item['message']}"
        )
    if not findings:
        print("PASS: No payment audit findings.")
    return findings
