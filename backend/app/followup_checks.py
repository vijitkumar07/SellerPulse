from sqlalchemy import text
from backend.app.database import engine
checks = {
    "fulfillment ID vs linked order-line business ID": """
        SELECT COUNT(*)
        FROM fulfillments f
        JOIN order_lines ol ON ol.id = f.order_line_id
        WHERE f.business_id != ('FUL-' || ol.id)
    """,
    "fulfillment ID vs linked order-line business ID with padding": """
        SELECT COUNT(*)
        FROM fulfillments f
        JOIN order_lines ol ON ol.id = f.order_line_id
        WHERE f.business_id != ('FUL-' || printf('%08d', ol.id))
    """,
    "fulfillments linked to non-delivered orders": """
        SELECT COUNT(*)
        FROM fulfillments f
        JOIN orders o ON o.id = f.order_id
        WHERE o.status != 'delivered'
    """,
    "late shipment candidates (shipped more than 2 days after order)": """
        SELECT COUNT(*)
        FROM fulfillments f
        JOIN orders o ON o.id = f.order_id
        WHERE f.shipped_at IS NOT NULL
          AND julianday(f.shipped_at) - julianday(o.created_at) > 2
    """,
    "orders with positive refund payout lines": """
        SELECT COUNT(DISTINCT order_id)
        FROM payout_lines WHERE refund_amount > 0
    """,
    "resolved disputes with matching payout lines": """
        SELECT COUNT(DISTINCT d.id)
        FROM disputes d
        JOIN payout_lines pl ON pl.order_id = d.order_id
        WHERE LOWER(d.status) = 'resolved'
    """,
    "resolved disputes with no payout line": """
        SELECT COUNT(*)
        FROM disputes d
        WHERE LOWER(d.status) = 'resolved'
          AND NOT EXISTS (
              SELECT 1 FROM payout_lines pl WHERE pl.order_id = d.order_id
          )
    """,
    "suspended sellers with active listings": """
        SELECT COUNT(*)
        FROM product_listings l
        JOIN sellers s ON s.id = l.seller_id
        WHERE LOWER(s.status) = 'suspended'
          AND LOWER(l.status) = 'active'
    """,
    "event rows without a status transition type": """
        SELECT COUNT(*)
        FROM entity_events
        WHERE event_type IS NULL OR TRIM(event_type) = ''
    """,
}
with engine.connect() as conn:
    print("SELLERPULSE FOLLOW-UP CHECKS")
    print("=" * 40)
    for label, query in checks.items():
        try:
            value = conn.execute(text(query)).scalar_one()
            print(f"{label}: {value}")
        except Exception as exc:
            print(f"{label}: CHECK ERROR - {exc}")
