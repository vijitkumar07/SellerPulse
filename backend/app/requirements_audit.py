import json
import re
from pathlib import Path
from collections import Counter
from sqlalchemy import inspect, text
from backend.app.database import engine
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "exports"
REPORT = OUT / "requirements_audit_step1.json"
ID_RULES = {
    "sellers": ("business_id", re.compile(r"^SELL-\d{6}$")),
    "product_listings": ("business_id", re.compile(r"^LIST-.+-\d{6}$")),
    "orders": ("business_id", re.compile(r"^ORD-2026-\d{6}$")),
    "fulfillments": ("business_id", re.compile(r"^FUL-.+$")),
    "disputes": ("business_id", re.compile(r"^DSP-2026-\d{6}$")),
    "payouts": ("business_id", re.compile(r"^PAYOUT-2026-\d{6}$")),
}
report = {
    "id_format_checks": {},
    "status_distributions": {},
    "coverage_counts": {},
    "table_counts": {},
    "notes": [],
}
with engine.connect() as conn:
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    # Actual row counts
    for table in sorted(tables):
        report["table_counts"][table] = int(
            conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
        )
    # Business ID pattern checks and representative samples
    for table, (column, pattern) in ID_RULES.items():
        if table not in tables:
            report["id_format_checks"][table] = {"status": "TABLE_MISSING"}
            continue
        columns = {c["name"] for c in inspector.get_columns(table)}
        if column not in columns:
            report["id_format_checks"][table] = {"status": "COLUMN_MISSING"}
            continue
        values = conn.execute(
            text(f'SELECT "{column}" FROM "{table}" ORDER BY id LIMIT 1000')
        ).scalars().all()
        total = report["table_counts"][table]
        valid = sum(
            1 for value in values
            if value is not None and pattern.fullmatch(str(value))
        )
        missing = sum(1 for value in values if not value)
        invalid_examples = [
            value for value in values
            if value is not None and not pattern.fullmatch(str(value))
        ][:10]
        # All rows must be checked, not only the sample.
        all_values = conn.execute(
            text(f'SELECT "{column}" FROM "{table}"')
        ).scalars().all()
        invalid_all = [
            value for value in all_values
            if value is None or not pattern.fullmatch(str(value))
        ]
        report["id_format_checks"][table] = {
            "rows": total,
            "valid_in_sample": valid,
            "sample_size": len(values),
            "invalid_or_missing_total": len(invalid_all),
            "invalid_examples": invalid_examples,
            "status": "PASS" if not invalid_all else "REVIEW",
        }
    # Status distributions expose actual generated coverage.
    for table in [
        "sellers", "product_listings", "orders", "fulfillments",
        "disputes", "payouts", "commission_rules"
    ]:
        if table not in tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "status" in cols:
            rows = conn.execute(text(
                f'SELECT LOWER(CAST(status AS TEXT)), COUNT(*) '
                f'FROM "{table}" GROUP BY LOWER(CAST(status AS TEXT)) '
                f'ORDER BY 1'
            )).all()
            report["status_distributions"][table] = {
                str(status): int(count) for status, count in rows
            }
    # Check coverage that can be derived directly from current schema.
    if "fulfillments" in tables:
        cols = {c["name"] for c in inspector.get_columns("fulfillments")}
        if {"shipped_at", "delivered_at"}.issubset(cols):
            report["coverage_counts"]["shipped_and_delivered"] = int(
                conn.execute(text("""
                    SELECT COUNT(*) FROM fulfillments
                    WHERE shipped_at IS NOT NULL AND delivered_at IS NOT NULL
                """)).scalar_one()
            )
            report["coverage_counts"]["delivered_without_shipment_date"] = int(
                conn.execute(text("""
                    SELECT COUNT(*) FROM fulfillments
                    WHERE delivered_at IS NOT NULL AND shipped_at IS NULL
                """)).scalar_one()
            )
    if "payout_lines" in tables:
        cols = {c["name"] for c in inspector.get_columns("payout_lines")}
        for column in ["refund_amount", "reserve_amount", "dispute_deduction"]:
            if column in cols:
                report["coverage_counts"][f"{column}_positive_lines"] = int(
                    conn.execute(text(
                        f'SELECT COUNT(*) FROM payout_lines '
                        f'WHERE "{column}" > 0'
                    )).scalar_one()
                )
    if "commission_rules" in tables:
        cols = {c["name"] for c in inspector.get_columns("commission_rules")}
        if "effective_from" in cols and "effective_to" in cols:
            report["coverage_counts"]["commission_rules_with_effective_dates"] = int(
                conn.execute(text("""
                    SELECT COUNT(*) FROM commission_rules
                    WHERE effective_from IS NOT NULL
                """)).scalar_one()
            )
    if "entity_events" in tables:
        report["coverage_counts"]["entity_event_count"] = report["table_counts"]["entity_events"]
        report["coverage_counts"]["distinct_event_entities"] = int(
            conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT entity_type, entity_id FROM entity_events
                )
            """)).scalar_one()
        )
    report["notes"].append(
        "This is a diagnostic report. Exact fulfillment ID suffix semantics, "
        "late-shipment definition, return coverage, and full lifecycle correctness "
        "require comparison with generator rules and documented business rules."
    )
OUT.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SELLERPULSE REQUIREMENTS AUDIT — STEP 1")
print("=" * 45)
print("TABLE COUNTS:")
for table, count in report["table_counts"].items():
    print(f"  {table}: {count}")
print("\nID FORMAT CHECKS:")
for table, info in report["id_format_checks"].items():
    print(f"  {table}: {info}")
print("\nSTATUS DISTRIBUTIONS:")
for table, distribution in report["status_distributions"].items():
    print(f"  {table}: {distribution}")
print("\nCOVERAGE COUNTS:")
for name, count in report["coverage_counts"].items():
    print(f"  {name}: {count}")
print(f"\nReport saved to: {REPORT}")
