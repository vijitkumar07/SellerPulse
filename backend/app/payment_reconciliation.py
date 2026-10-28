
from pathlib import Path
import json
import sys

from backend.app.database import SessionLocal
from backend.app.models import (
    Seller, ProductListing, Order, Dispute, Payout, PayoutLine
)
from backend.app.payment_audit import audit_payments

ROOT = Path(__file__).resolve().parents[2]
GT_PATH = ROOT / "data" / "ground_truth.json"
TOLERANCE = 0.01


def money(value):
    return round(float(value or 0), 2)


def main():
    if not GT_PATH.exists():
        print(f"FAIL: Ground truth file not found: {GT_PATH}")
        return 1

    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    expected = gt.get("anomalies", {})
    db = SessionLocal()

    try:
        sellers = {x.id: x for x in db.query(Seller).all()}
        listings = db.query(ProductListing).all()
        orders = {x.id: x for x in db.query(Order).all()}
        disputes = db.query(Dispute).all()
        payouts = {x.id: x for x in db.query(Payout).all()}
        lines = db.query(PayoutLine).all()

        print("SELLERPULSE PAYMENT RECONCILIATION")
        print("-" * 46)

        # 1. Verify payout line arithmetic.
        bad_lines = []
        for line in lines:
            gross = money(line.gross_amount)
            commission = money(line.commission_amount)
            dispute = money(line.dispute_deduction)
            refund = money(line.refund_amount)
            reserve = money(line.reserve_amount)
            net = money(line.net_amount)

            expected_net = round(
                gross - commission - dispute - refund - reserve, 2
            )

            if abs(net - expected_net) > TOLERANCE:
                bad_lines.append(
                    (line.id, "net mismatch", expected_net, net)
                )

            if min(gross, commission, dispute, refund, reserve, net) < 0:
                bad_lines.append((line.id, "negative amount"))

            if commission + dispute + refund + reserve > gross + TOLERANCE:
                bad_lines.append((line.id, "deductions exceed gross"))

        print(f"Payout lines checked: {len(lines)}")
        print(f"Line arithmetic errors: {len(bad_lines)}")
        for issue in bad_lines[:10]:
            print("  ERROR:", issue)

        # 2. Verify payout header totals against line totals.
        lines_by_payout = {}
        for line in lines:
            lines_by_payout.setdefault(line.payout_id, []).append(line)

        header_mismatches = []
        for payout in payouts.values():
            total = round(
                sum(money(x.net_amount)
                    for x in lines_by_payout.get(payout.id, [])),
                2,
            )
            if abs(money(payout.total_amount) - total) > TOLERANCE:
                header_mismatches.append(payout.id)

        expected_header_ids = set(
            expected.get("payout_total_mismatch", [])
        )
        actual_header_ids = set(header_mismatches)

        print(f"Payout headers checked: {len(payouts)}")
        print(f"Header mismatches: {len(header_mismatches)}")
        print(
            "Unexpected header mismatches:",
            len(actual_header_ids - expected_header_ids),
        )

        # 3. Check resolved disputes only when a corresponding payout line
        # exists. No payout line means no deduction can yet be reconciled.
        lines_by_order = {}
        for line in lines:
            lines_by_order.setdefault(line.order_id, []).append(line)

        intentional_line_ids = set(
            expected.get("dispute_not_deducted", [])
        )
        intentional_orders = {
            line.order_id
            for line in lines
            if line.id in intentional_line_ids
        }

        missing_disputes = []
        checked_disputes = 0
        no_payout_disputes = 0
        intentional_exceptions = 0

        for dispute in disputes:
            if str(dispute.status).lower() != "resolved":
                continue

            order = orders.get(dispute.order_id)
            related = lines_by_order.get(dispute.order_id, [])

            # Restrict comparison to the order's seller where applicable.
            if order is not None:
                related = [
                    line for line in related
                    if line.payout_id in payouts
                    and payouts[line.payout_id].seller_id == order.seller_id
                ]

            if not related:
                no_payout_disputes += 1
                continue

            checked_disputes += 1

            if dispute.order_id in intentional_orders:
                intentional_exceptions += 1
                continue

            deducted = sum(
                money(line.dispute_deduction) for line in related
            )

            if deducted + TOLERANCE < money(dispute.amount):
                missing_disputes.append(dispute.id)

        print(f"Resolved disputes checked with payouts: {checked_disputes}")
        print(f"Resolved disputes without payout lines: {no_payout_disputes}")
        print(f"Intentional dispute exceptions: {intentional_exceptions}")
        print(f"Unexpected missing dispute deductions: {len(missing_disputes)}")

        # 4. Compare payment audit findings with ground truth.
        findings = audit_payments(db)
        actual_pairs = {
            (item["rule"], str(item["record_id"]))
            for item in findings
        }

        expected_pairs = set()

        for scenario, rule in [
            ("suspended_seller_listing_active",
             "suspended_seller_listing_active"),
            ("payout_before_delivery_or_hold_release",
             "payout_before_delivery_or_hold_release"),
            ("commission_applied_twice", "commission_applied_twice"),
            ("payout_total_mismatch", "payout_total_mismatch"),
        ]:
            expected_pairs.update(
                (rule, str(record_id))
                for record_id in expected.get(scenario, [])
            )

        # Ground truth stores the payout-line ID, while the audit reports
        # the related dispute ID for this intentional anomaly.
        for line_id in intentional_line_ids:
            anomaly_line = next(
                (line for line in lines if line.id == line_id), None
            )
            if anomaly_line:
                for dispute in disputes:
                    if dispute.order_id == anomaly_line.order_id:
                        expected_pairs.add(
                            ("dispute_deduction_missing", str(dispute.id))
                        )

        unexpected_findings = actual_pairs - expected_pairs
        undetected_findings = expected_pairs - actual_pairs

        print(f"Audit findings: {len(findings)}")
        print(f"Expected ground-truth findings: {len(expected_pairs)}")
        print(f"Unexpected audit findings: {len(unexpected_findings)}")
        print(f"Expected findings not detected: {len(undetected_findings)}")

        if unexpected_findings:
            print("  Unexpected:", sorted(unexpected_findings))
        if undetected_findings:
            print("  Not detected:", sorted(undetected_findings))
        if missing_disputes:
            print("  Missing deductions:", missing_disputes[:10])

        failures = (
            bool(bad_lines)
            or bool(actual_header_ids - expected_header_ids)
            or bool(expected_header_ids - actual_header_ids)
            or bool(missing_disputes)
            or actual_pairs != expected_pairs
        )

        print("-" * 46)
        if failures:
            print("RESULT: FAIL — inspect the errors above.")
            return 1

        print("RESULT: PASS — reconciliation checks passed.")
        print("Documented intentional anomalies remain correctly labelled.")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
