
import csv
import json
import hashlib
from pathlib import Path

from sqlalchemy import inspect, text

from .database import engine

ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = ROOT / "data" / "exports"
GROUND_TRUTH_PATH = ROOT / "data" / "ground_truth.json"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

TABLES = [
    "sellers",
    "product_listings",
    "orders",
    "order_lines",
    "order_sellers",
    "fulfillments",
    "customer_reviews",
    "disputes",
    "commission_rules",
    "payouts",
    "payout_lines",
    "entity_events",
]


def export_table(connection, table_name):
    result = connection.execute(text(f'SELECT * FROM "{table_name}"'))
    columns = list(result.keys())
    rows = result.fetchall()

    csv_path = EXPORT_DIR / f"{table_name}.csv"
    json_path = EXPORT_DIR / f"{table_name}.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    json_rows = [dict(zip(columns, row)) for row in rows]

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(json_rows, file, indent=2, default=str)

    checksum = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    return {
        "table": table_name,
        "rows": len(rows),
        "csv": csv_path.name,
        "json": json_path.name,
        "sha256_csv": checksum,
    }


def validate_database(connection):
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    errors = []

    # Required tables and primary keys.
    for table in TABLES:
        if table not in tables:
            errors.append(f"Missing table: {table}")
            continue

        pk = inspector.get_pk_constraint(table)
        if not pk.get("constrained_columns"):
            errors.append(f"{table}: primary key missing")

        # Foreign-key integrity, including composite relationships.
        for fk in inspector.get_foreign_keys(table):
            child_columns = fk.get("constrained_columns", [])
            parent_columns = fk.get("referred_columns", [])
            parent_table = fk.get("referred_table")

            if (
                not child_columns
                or len(child_columns) != len(parent_columns)
                or not parent_table
            ):
                errors.append(f"{table}: malformed foreign key definition")
                continue

            conditions = " AND ".join(
                f'parent."{parent_col}" = child."{child_col}"'
                for child_col, parent_col in zip(
                    child_columns, parent_columns
                )
            )
            non_null_conditions = " AND ".join(
                f'child."{column}" IS NOT NULL'
                for column in child_columns
            )

            query = text(
                f'SELECT COUNT(*) FROM "{table}" child '
                f'WHERE {non_null_conditions} '
                f'AND NOT EXISTS ('
                f'SELECT 1 FROM "{parent_table}" parent '
                f'WHERE {conditions})'
            )
            orphan_count = connection.execute(query).scalar_one()

            if orphan_count:
                errors.append(
                    f"{table}.{','.join(child_columns)}: "
                    f"{orphan_count} orphan foreign-key rows"
                )

    if "payout_lines" in tables:
        # Net = gross - commission - disputes - refunds - reserves.
        payout_arithmetic_errors = connection.execute(text("""
            SELECT COUNT(*)
            FROM payout_lines
            WHERE ABS(
                net_amount -
                (
                    gross_amount
                    - commission_amount
                    - dispute_deduction
                    - refund_amount
                    - reserve_amount
                )
            ) > 0.02
        """)).scalar_one()

        if payout_arithmetic_errors:
            errors.append(
                f"Payout arithmetic mismatches in "
                f"{payout_arithmetic_errors} lines"
            )

    if {"payouts", "payout_lines"}.issubset(tables):
        # Header totals must match their payout-line totals, except for
        # explicitly labelled seeded anomalies verified in main().
        payout_total_errors = connection.execute(text("""
            SELECT COUNT(*)
            FROM payouts p
            WHERE EXISTS (
                SELECT 1
                FROM payout_lines pl
                WHERE pl.payout_id = p.id
            )
            AND ABS(
                p.total_amount - (
                    SELECT COALESCE(SUM(pl.net_amount), 0)
                    FROM payout_lines pl
                    WHERE pl.payout_id = p.id
                )
            ) > 0.02
        """)).scalar_one()

        if payout_total_errors:
            errors.append(
                "Payout header/line total mismatches in "
                f"{payout_total_errors} payouts"
            )

    # Required business IDs must be populated and unique.
    business_id_columns = {
        "sellers": "business_id",
        "product_listings": "business_id",
        "orders": "business_id",
        "order_lines": "business_id",
        "fulfillments": "business_id",
        "disputes": "business_id",
        "payouts": "business_id",
    }

    for table, column in business_id_columns.items():
        if table not in tables:
            continue

        available_columns = {
            item["name"] for item in inspector.get_columns(table)
        }
        if column not in available_columns:
            errors.append(f"{table}: missing {column} column")
            continue

        missing_count = connection.execute(text(
            f'SELECT COUNT(*) FROM "{table}" '
            f'WHERE "{column}" IS NULL OR TRIM("{column}") = \'\''
        )).scalar_one()

        if missing_count:
            errors.append(
                f"{table}.{column}: {missing_count} missing business IDs"
            )

        duplicate_count = connection.execute(text(
            f'SELECT COUNT(*) FROM ('
            f'SELECT "{column}" FROM "{table}" '
            f'GROUP BY "{column}" HAVING COUNT(*) > 1)'
        )).scalar_one()

        if duplicate_count:
            errors.append(
                f"{table}.{column}: {duplicate_count} duplicate ID groups"
            )

    # Every order line should have a fulfillment.
    if {"order_lines", "fulfillments"}.issubset(tables):
        missing_fulfillments = connection.execute(text("""
            SELECT COUNT(*)
            FROM order_lines ol
            WHERE NOT EXISTS (
                SELECT 1
                FROM fulfillments f
                WHERE f.order_line_id = ol.id
            )
        """)).scalar_one()

        if missing_fulfillments:
            errors.append(
                f"{missing_fulfillments} order lines lack fulfillment records"
            )

    # Order totals must reconcile with source order lines.
    if {"orders", "order_lines"}.issubset(tables):
        total_mismatches = connection.execute(text("""
            SELECT COUNT(*)
            FROM orders o
            WHERE ABS(
                o.total_amount - (
                    SELECT COALESCE(SUM(ol.quantity * ol.unit_price), 0)
                    FROM order_lines ol
                    WHERE ol.order_id = o.id
                )
            ) > 0.02
        """)).scalar_one()

        if total_mismatches:
            errors.append(
                f"Order total mismatches in {total_mismatches} orders"
            )

    return errors


def get_ground_truth():
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Ground-truth file missing: {GROUND_TRUTH_PATH}"
        )

    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))



def main():
    summary = {
        "database": "SQLite",
        "tables": [],
        "validation_errors": [],
        "intentional_anomalies": [],
    }
    ground_truth = get_ground_truth()
    expected = ground_truth.get("anomalies", {})
    scenario_queries = {
        "payout_before_delivery_or_hold_release": """
            SELECT p.id
            FROM payouts p
            WHERE p.id = :rid
              AND EXISTS (
                SELECT 1 FROM payout_lines pl
                WHERE pl.payout_id = p.id
              )
              AND (
                p.hold_released_at IS NULL
                OR p.created_at < p.hold_released_at
                OR EXISTS (
                    SELECT 1
                    FROM payout_lines pl
                    JOIN orders o ON o.id = pl.order_id
                    WHERE pl.payout_id = p.id
                      AND (
                        o.status != 'delivered'
                        OR NOT EXISTS (
                            SELECT 1 FROM fulfillments f
                            WHERE f.order_id = o.id
                              AND f.delivered_at IS NOT NULL
                        )
                        OR EXISTS (
                            SELECT 1 FROM fulfillments f
                            WHERE f.order_id = o.id
                              AND (
                                f.status != 'delivered'
                                OR f.delivered_at IS NULL
                                OR p.created_at < f.delivered_at
                              )
                        )
                      )
                )
              )
        """,
        "commission_applied_twice": """
            SELECT pl.id
            FROM payout_lines pl
            WHERE pl.id = :rid
              AND EXISTS (
                SELECT 1 FROM payouts p
                WHERE p.id = pl.payout_id
              )
              AND pl.commission_amount > pl.gross_amount * 0.10 + 0.01
        """,
        "suspended_seller_listing_active": """
            SELECT l.id
            FROM product_listings l
            JOIN sellers s ON s.id = l.seller_id
            WHERE l.id = :rid
              AND LOWER(s.status) = 'suspended'
              AND LOWER(l.status) = 'active'
        """,
        "dispute_not_deducted": """
            SELECT pl.id
            FROM payout_lines pl
            JOIN disputes d ON d.order_id = pl.order_id
            WHERE pl.id = :rid
              AND LOWER(d.status) = 'resolved'
              AND COALESCE(pl.dispute_deduction, 0) + 0.01 < d.amount
        """,
        "payout_total_mismatch": """
            SELECT p.id
            FROM payouts p
            WHERE p.id = :rid
              AND EXISTS (
                SELECT 1 FROM payout_lines pl
                WHERE pl.payout_id = p.id
              )
              AND ABS(
                p.total_amount - (
                  SELECT COALESCE(SUM(pl.net_amount), 0)
                  FROM payout_lines pl
                  WHERE pl.payout_id = p.id
                )
              ) > 0.02
        """,
    }
    with engine.connect() as connection:
        available_tables = set(inspect(connection).get_table_names())
        for table in TABLES:
            if table not in available_tables:
                summary["validation_errors"].append(
                    f"Cannot export missing table: {table}"
                )
                continue
            summary["tables"].append(export_table(connection, table))
        validation_errors = validate_database(connection)
        expected_mismatch_ids = set(
            expected.get("payout_total_mismatch", [])
        )
        actual_mismatch_ids = set(
            connection.execute(text("""
                SELECT p.id
                FROM payouts p
                WHERE EXISTS (
                    SELECT 1 FROM payout_lines pl
                    WHERE pl.payout_id = p.id
                )
                AND ABS(
                    p.total_amount - (
                        SELECT COALESCE(SUM(pl.net_amount), 0)
                        FROM payout_lines pl
                        WHERE pl.payout_id = p.id
                    )
                ) > 0.02
            """)).scalars().all()
        )
        if expected_mismatch_ids and actual_mismatch_ids == expected_mismatch_ids:
            validation_errors = [
                error for error in validation_errors
                if not error.startswith("Payout header/line total mismatches")
            ]
        elif actual_mismatch_ids != expected_mismatch_ids:
            validation_errors.append(
                "Payout header/line mismatch IDs differ from ground truth: "
                f"expected {sorted(expected_mismatch_ids)}, "
                f"found {sorted(actual_mismatch_ids)}"
            )
        summary["validation_errors"].extend(validation_errors)
        verified_ids = {}
        for scenario, ids in expected.items():
            if scenario not in scenario_queries:
                summary["validation_errors"].append(
                    f"No verification rule defined for scenario: {scenario}"
                )
                continue
            actual = set()
            for record_id in ids:
                try:
                    found = connection.execute(
                        text(scenario_queries[scenario]),
                        {"rid": record_id},
                    ).scalars().first()
                    if found is not None:
                        actual.add(found)
                except Exception as exc:
                    summary["validation_errors"].append(
                        f"Could not verify {scenario} record {record_id}: {exc}"
                    )
            verified_ids[scenario] = sorted(actual)
            expected_set = set(ids)
            if actual != expected_set:
                summary["validation_errors"].append(
                    f"Ground-truth mismatch for {scenario}: "
                    f"expected {sorted(expected_set)}, found {sorted(actual)}"
                )
            else:
                summary["intentional_anomalies"].append({
                    "scenario": scenario,
                    "record_ids": sorted(actual),
                    "validation_note": "Record IDs and anomaly conditions verified.",
                })
    report_path = EXPORT_DIR / "validation_summary.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Export complete.")
    print(f"Output folder: {EXPORT_DIR}")
    print(f"Tables exported: {len(summary['tables'])}")
    print(
        "Intentional anomalies verified: "
        f"{len(summary['intentional_anomalies'])}/"
        f"{len(expected)}"
    )
    print(f"Validation errors: {len(summary['validation_errors'])}")
    for error in summary["validation_errors"]:
        print(f"VALIDATION ERROR: {error}")
    if summary["validation_errors"]:
        raise SystemExit(1)
if __name__ == "__main__":
    main()
