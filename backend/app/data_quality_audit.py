import json
from pathlib import Path
from sqlalchemy import inspect, text
from backend.app.database import engine
from backend.app.models import Base
from backend.app.data_dictionary import FIELD_RULES
ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "data" / "exports" / "data_quality_audit.json"
EXPECTED_TABLES = set(Base.metadata.tables)
results = {}
errors = []
def scalar(conn, query):
    return int(conn.execute(text(query)).scalar_one())
with engine.connect() as conn:
    inspector = inspect(conn)
    db_tables = set(inspector.get_table_names())
    missing_tables = sorted(EXPECTED_TABLES - db_tables)
    results["missing_model_tables"] = missing_tables
    if missing_tables:
        errors.append(f"Missing model tables: {missing_tables}")
    pk_checks = {}
    fk_checks = {}
    for table in sorted(EXPECTED_TABLES & db_tables):
        model_table = Base.metadata.tables[table]
        pk_columns = [c.name for c in model_table.primary_key.columns]
        pk_checks[table] = pk_columns
        if not pk_columns:
            errors.append(f"{table}: model has no primary key")
        # Duplicate primary-key groups
        group_cols = ", ".join(f'"{c}"' for c in pk_columns)
        duplicates = scalar(
            conn,
            f'SELECT COUNT(*) FROM (SELECT {group_cols} FROM "{table}" '
            f'GROUP BY {group_cols} HAVING COUNT(*) > 1)'
        ) if pk_columns else 0
        if duplicates:
            errors.append(f"{table}: {duplicates} duplicate primary-key groups")
        # Null primary-key values
        if pk_columns:
            null_condition = " OR ".join(
                f'"{c}" IS NULL' for c in pk_columns
            )
            null_count = scalar(
                conn, f'SELECT COUNT(*) FROM "{table}" WHERE {null_condition}'
            )
            if null_count:
                errors.append(f"{table}: {null_count} null primary-key rows")
        # Check actual foreign-key references
        for fk in inspector.get_foreign_keys(table):
            child_cols = fk.get("constrained_columns") or []
            parent_cols = fk.get("referred_columns") or []
            parent_table = fk.get("referred_table")
            if not child_cols or len(child_cols) != len(parent_cols):
                errors.append(f"{table}: malformed foreign-key definition")
                continue
            non_null = " AND ".join(
                f'c."{col}" IS NOT NULL' for col in child_cols
            )
            match = " AND ".join(
                f'p."{parent}" = c."{child}"'
                for child, parent in zip(child_cols, parent_cols)
            )
            orphan_count = scalar(
                conn,
                f'SELECT COUNT(*) FROM "{table}" c '
                f'WHERE {non_null} AND NOT EXISTS '
                f'(SELECT 1 FROM "{parent_table}" p WHERE {match})'
            )
            key = f"{table}.{','.join(child_cols)}->{parent_table}"
            fk_checks[key] = orphan_count
            if orphan_count:
                errors.append(f"{key}: {orphan_count} orphan rows")
    results["primary_keys"] = pk_checks
    results["foreign_key_orphans"] = fk_checks
    # Business IDs should be present and unique where expected.
    business_id_tables = [
        "sellers", "product_listings", "orders", "order_lines",
        "fulfillments", "disputes", "payouts"
    ]
    business_id_checks = {}
    for table in business_id_tables:
        if table not in db_tables:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "business_id" not in cols:
            errors.append(f"{table}: missing business_id column")
            continue
        missing = scalar(
            conn, f'SELECT COUNT(*) FROM "{table}" '
            'WHERE business_id IS NULL OR TRIM(business_id) = \'\''
        )
        duplicates = scalar(
            conn, f'SELECT COUNT(*) FROM ('
            f'SELECT business_id FROM "{table}" '
            'GROUP BY business_id HAVING COUNT(*) > 1)'
        )
        business_id_checks[table] = {
            "missing": missing, "duplicate_groups": duplicates
        }
        if missing:
            errors.append(f"{table}: {missing} missing business IDs")
        if duplicates:
            errors.append(f"{table}: {duplicates} duplicate business IDs")
    results["business_ids"] = business_id_checks
    # Fulfillment chronology: shipment cannot be after delivery.
    if "fulfillments" in db_tables:
        bad_dates = scalar(conn, """
            SELECT COUNT(*) FROM fulfillments
            WHERE shipped_at IS NOT NULL
              AND delivered_at IS NOT NULL
              AND shipped_at > delivered_at
        """)
        results["fulfillment_date_order_errors"] = bad_dates
        if bad_dates:
            errors.append(f"{bad_dates} fulfillment shipment/delivery date errors")
        # If linked to an order line, both records must refer to the same order.
        mismatches = scalar(conn, """
            SELECT COUNT(*)
            FROM fulfillments f
            JOIN order_lines ol ON ol.id = f.order_line_id
            WHERE f.order_id != ol.order_id
        """) if {"order_lines", "fulfillments"}.issubset(db_tables) else 0
        results["fulfillment_order_line_mismatches"] = mismatches
        if mismatches:
            errors.append(f"{mismatches} fulfillment/order-line mismatches")
        # Each order line should have at least one fulfillment.
        missing_fulfillment = scalar(conn, """
            SELECT COUNT(*) FROM order_lines ol
            WHERE NOT EXISTS (
                SELECT 1 FROM fulfillments f
                WHERE f.order_line_id = ol.id
            )
        """) if {"order_lines", "fulfillments"}.issubset(db_tables) else 0
        results["order_lines_without_fulfillment"] = missing_fulfillment
        if missing_fulfillment:
            errors.append(f"{missing_fulfillment} order lines lack fulfillment")
    # Multi-seller relationship checks.
    if {"orders", "order_lines", "product_listings", "order_sellers"}.issubset(db_tables):
        line_seller_mismatches = scalar(conn, """
            SELECT COUNT(*)
            FROM order_lines ol
            JOIN product_listings l ON l.id = ol.listing_id
            WHERE NOT EXISTS (
                SELECT 1 FROM order_sellers os
                WHERE os.order_id = ol.order_id
                  AND os.seller_id = l.seller_id
            )
        """)
        results["order_line_seller_link_mismatches"] = line_seller_mismatches
        if line_seller_mismatches:
            errors.append(
                f"{line_seller_mismatches} order lines missing their seller bridge link"
            )
        orders_without_seller_links = scalar(conn, """
            SELECT COUNT(*) FROM orders o
            WHERE NOT EXISTS (
                SELECT 1 FROM order_sellers os WHERE os.order_id = o.id
            )
        """)
        results["orders_without_seller_links"] = orders_without_seller_links
        if orders_without_seller_links:
            errors.append(f"{orders_without_seller_links} orders lack seller links")
        seller_count = scalar(conn, """
            SELECT COUNT(*) FROM (
                SELECT order_id FROM order_sellers
                GROUP BY order_id HAVING COUNT(DISTINCT seller_id) > 1
            )
        """)
        results["multi_seller_order_count"] = seller_count
    # Order total should match line quantity * unit price.
    if {"orders", "order_lines"}.issubset(db_tables):
        total_mismatches = scalar(conn, """
            SELECT COUNT(*) FROM orders o
            WHERE ABS(o.total_amount - (
                SELECT COALESCE(SUM(ol.quantity * ol.unit_price), 0)
                FROM order_lines ol WHERE ol.order_id = o.id
            )) > 0.02
        """)
        results["order_total_mismatches"] = total_mismatches
        if total_mismatches:
            errors.append(f"{total_mismatches} order total mismatches")
    # Compare data-dictionary field names with actual model columns.
    # FIELD_RULES may be a mapping or a list of field dictionaries.
    dictionary_fields = {}
    if isinstance(FIELD_RULES, dict):
        for table, rules in FIELD_RULES.items():
            if isinstance(rules, dict):
                dictionary_fields[str(table)] = set(map(str, rules.keys()))
            elif isinstance(rules, list):
                names = {
                    str(item.get("name") or item.get("field"))
                    for item in rules if isinstance(item, dict)
                    if item.get("name") or item.get("field")
                }
                dictionary_fields[str(table)] = names
    elif isinstance(FIELD_RULES, list):
        for item in FIELD_RULES:
            if not isinstance(item, dict):
                continue
            table = item.get("table") or item.get("table_name")
            field = item.get("name") or item.get("field") or item.get("column")
            if table and field:
                dictionary_fields.setdefault(str(table), set()).add(str(field))
    dictionary_report = {}
    for table, fields in dictionary_fields.items():
        normalized = table.lower()
        if normalized not in EXPECTED_TABLES:
            continue
        actual_fields = set(Base.metadata.tables[normalized].columns.keys())
        dictionary_report[normalized] = {
            "missing_from_dictionary": sorted(actual_fields - fields),
            "unknown_in_dictionary": sorted(fields - actual_fields),
        }
        if actual_fields - fields:
            errors.append(
                f"{normalized}: model columns missing from dictionary: "
                f"{sorted(actual_fields - fields)}"
            )
        if fields - actual_fields:
            errors.append(
                f"{normalized}: unknown dictionary fields: "
                f"{sorted(fields - actual_fields)}"
            )
    results["data_dictionary_comparison"] = dictionary_report
    results["dictionary_table_count_compared"] = len(dictionary_report)
results["error_count"] = len(errors)
results["errors"] = errors
results["status"] = "PASS" if not errors else "FAIL"
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("SELLERPULSE DATA QUALITY AUDIT")
print("=" * 42)
for key, value in results.items():
    if key not in {"primary_keys", "foreign_key_orphans", "business_ids",
                   "data_dictionary_comparison", "errors"}:
        print(f"{key}: {value}")
print(f"Report: {REPORT}")
for error in errors:
    print("ERROR:", error)
print("RESULT:", results["status"])
