
import json
import csv
from pathlib import Path
from sqlalchemy import inspect

from .database import engine

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "exports"
OUT.mkdir(parents=True, exist_ok=True)

FIELD_DESCRIPTIONS = {
    ("sellers", "business_id"): "Stable external seller ID in SELL-###### format.",
    ("sellers", "status"): "Seller account state; suspended sellers should not have active listings.",
    ("product_listings", "business_id"): "Stable listing ID containing seller ID and seller-local sequence.",
    ("product_listings", "seller_id"): "Internal ID of the seller owning this listing.",
    ("product_listings", "price"): "Listing unit price in synthetic currency units.",
    ("orders", "business_id"): "Stable external order ID in ORD-2026-###### format.",
    ("orders", "seller_id"): "Primary seller associated with this order for payout reconciliation.",
    ("orders", "total_amount"): "Sum of the order line totals in synthetic currency units.",
    ("order_lines", "business_id"): "Stable external order-line ID in LINE-######## format.",
    ("order_lines", "order_id"): "Order containing this order line.",
    ("order_lines", "listing_id"): "Product listing purchased on this line.",
    ("order_lines", "quantity"): "Number of units purchased; expected to be a positive integer.",
    ("order_lines", "unit_price"): "Price per unit at order time in synthetic currency units.",
    ("fulfillments", "business_id"): "Stable fulfillment ID derived from the related order-line ID.",
    ("fulfillments", "order_id"): "Order being fulfilled.",
    ("fulfillments", "order_line_id"): "Order line handled by this fulfillment.",
    ("fulfillments", "shipped_at"): "Timestamp when shipment was dispatched.",
    ("fulfillments", "delivered_at"): "Delivery timestamp; null until delivery.",
    ("customer_reviews", "order_id"): "Order reviewed by the customer.",
    ("customer_reviews", "rating"): "Customer rating from 1 to 5 stars.",
    ("disputes", "business_id"): "Stable external dispute ID in DSP-2026-###### format.",
    ("disputes", "order_id"): "Order associated with the dispute.",
    ("disputes", "amount"): "Disputed amount in synthetic currency units.",
    ("disputes", "status"): "Dispute state: open or resolved.",
    ("commission_rules", "rate"): "Commission fraction; 0.10 represents 10 percent.",
    ("commission_rules", "effective_from"): "Inclusive timestamp when this commission rule starts applying.",
    ("commission_rules", "effective_to"): "Rule end timestamp; null means no scheduled end.",
    ("payouts", "business_id"): "Stable external payout ID in PAYOUT-2026-###### format.",
    ("payouts", "seller_id"): "Seller receiving the payout.",
    ("payouts", "total_amount"): "Payout header total; should match its payout-line net total.",
    ("payouts", "hold_released_at"): "Timestamp the payout hold was released; null while unreleased.",
    ("payout_lines", "payout_id"): "Payout header containing this line.",
    ("payout_lines", "order_id"): "Order whose seller proceeds are represented by this line.",
    ("payout_lines", "gross_amount"): "Seller gross proceeds before deductions.",
    ("payout_lines", "commission_amount"): "Commission withheld from seller gross proceeds.",
    ("payout_lines", "dispute_deduction"): "Resolved-dispute amount withheld from seller proceeds.",
    ("payout_lines", "refund_amount"): "Refund amount withheld from seller proceeds.",
    ("payout_lines", "reserve_amount"): "Reserve retained from seller proceeds.",
    ("payout_lines", "net_amount"): "Gross minus commission, dispute deduction, refund, and reserve.",
    ("entity_events", "entity_type"): "Entity category whose lifecycle event is recorded.",
    ("entity_events", "entity_id"): "External identifier of the entity whose lifecycle changed.",
    ("entity_events", "event_type"): "Event category, such as creation or status change.",
    ("entity_events", "old_value"): "Previous state; null for the initial event.",
    ("entity_events", "new_value"): "State after the event.",
    ("entity_events", "occurred_at"): "Timestamp when the event occurred.",
    ("entity_events", "details"): "Human-readable explanation of the synthetic event.",
    ("commission_rules", "id"): "Internal primary key identifying this commission rule.",
    ("commission_rules", "seller_id"): "Optional seller-specific scope; null means the rule applies to all sellers.",
    ("commission_rules", "is_active"): "Whether the commission rule is eligible for payout calculations.",
    ("customer_reviews", "id"): "Internal primary key identifying this customer review.",
    ("customer_reviews", "comment"): "Text feedback submitted by the customer for the reviewed order.",
    ("disputes", "id"): "Internal primary key identifying this dispute.",
    ("disputes", "created_at"): "Timestamp when the dispute record was created.",
    ("entity_events", "id"): "Internal primary key identifying this lifecycle event.",
    ("fulfillments", "id"): "Internal primary key identifying this fulfillment record.",
    ("fulfillments", "status"): "Fulfillment state; processing, shipped, or delivered.",
    ("order_lines", "id"): "Internal primary key identifying this order line.",
    ("order_sellers", "order_id"): "Order associated with this seller participation record.",
    ("order_sellers", "seller_id"): "Seller participating in the associated order.",
    ("order_sellers", "created_at"): "Timestamp when the order-seller association was recorded.",
    ("orders", "id"): "Internal primary key identifying the order.",
    ("orders", "status"): "Order lifecycle state; processing, shipped, or delivered.",
    ("orders", "created_at"): "Timestamp when the order was created.",
    ("payout_lines", "id"): "Internal primary key identifying this payout line.",
    ("payouts", "id"): "Internal primary key identifying the payout header.",
    ("payouts", "status"): "Payout processing state, such as pending, held, or paid.",
    ("payouts", "created_at"): "Timestamp when the payout record was created or paid.",
    ("product_listings", "id"): "Internal primary key identifying the product listing.",
    ("product_listings", "title"): "Display title of the listed product.",
    ("product_listings", "status"): "Listing availability state; active listings can be purchased.",
    ("sellers", "id"): "Internal primary key identifying the seller.",
    ("sellers", "name"): "Display name of the seller account.",
    ("sellers", "created_at"): "Timestamp when the seller account was created.",
}


# Business rules that cannot be inferred from SQL column types alone.
FIELD_RULES = {
    ("sellers", "status"): {
        "allowed_values": ["active", "suspended"],
        "units": None,
    },
    ("product_listings", "status"): {
        "allowed_values": ["active", "inactive"],
        "units": None,
    },
    ("orders", "status"): {
        "allowed_values": ["delivered", "shipped", "processing"],
        "units": None,
    },
    ("fulfillments", "status"): {
        "allowed_values": ["delivered", "shipped", "processing"],
        "units": None,
    },
    ("disputes", "status"): {
        "allowed_values": ["open", "resolved"],
        "units": None,
    },
    ("payouts", "status"): {
        "allowed_values": ["paid", "pending", "held"],
        "units": None,
    },
    ("customer_reviews", "rating"): {
        "allowed_values": "Integer from 1 to 5",
        "units": "stars",
    },
    ("product_listings", "price"): {"units": "currency units"},
    ("orders", "total_amount"): {"units": "currency units"},
    ("order_lines", "unit_price"): {"units": "currency units"},
    ("disputes", "amount"): {"units": "currency units"},
    ("commission_rules", "rate"): {"units": "fraction; 0.10 = 10%"},
    ("payouts", "total_amount"): {"units": "currency units"},
    ("payout_lines", "gross_amount"): {"units": "currency units"},
    ("payout_lines", "commission_amount"): {"units": "currency units"},
    ("payout_lines", "dispute_deduction"): {"units": "currency units"},
    ("payout_lines", "net_amount"): {"units": "currency units"},
    ("order_lines", "quantity"): {"units": "items"},
    ("payout_lines", "refund_amount"): {"units": "currency units"},
    ("payout_lines", "reserve_amount"): {"units": "currency units"},
}

def main():
    inspector = inspect(engine)
    dictionary = []

    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        pk_columns = set(
            inspector.get_pk_constraint(table).get("constrained_columns") or []
        )
        foreign_keys = {}

        for fk in inspector.get_foreign_keys(table):
            for index, column in enumerate(fk["constrained_columns"]):
                foreign_keys[column] = (
                    f'{fk["referred_table"]}.{fk["referred_columns"][index]}'
                )

        unique_columns = set()
        for constraint in inspector.get_unique_constraints(table):
            unique_columns.update(constraint.get("column_names") or [])

        for column in columns:
            name = column["name"]
            rules = FIELD_RULES.get((table, name), {})

            dictionary.append({
                "table": table,
                "field": name,
                "data_type": str(column["type"]),
                "required": not column.get("nullable", True),
                "primary_key": name in pk_columns,
                "foreign_key": foreign_keys.get(name),
                "unique": name in unique_columns or name in pk_columns,
                "default": str(column.get("default"))
                    if column.get("default") is not None else None,
                "allowed_values": rules.get("allowed_values"),
                "units": rules.get("units"),
                "description": FIELD_DESCRIPTIONS.get((table, name), f"{table}.{name}: database field; refer to its type, nullability, and key constraints."),
                "validation_notes": (
                    ("Required; " if not column.get("nullable", True) else "Nullable; ")
                    + ("primary key; " if name in pk_columns else "")
                    + (f"foreign key to {foreign_keys[name]}; " if name in foreign_keys else "")
                    + ("unique; " if name in unique_columns and name not in pk_columns else "")
                    + (f"Allowed values: {rules.get('allowed_values')}; " if rules.get("allowed_values") else "")
                    + (f"Units: {rules.get('units')}." if rules.get("units") else "Apply documented table-level business rules.")
                ),
            })

    json_path = OUT / "data_dictionary.json"
    csv_path = OUT / "data_dictionary.csv"

    json_path.write_text(
        json.dumps(dictionary, indent=2),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=dictionary[0].keys())
        writer.writeheader()
        writer.writerows(dictionary)

    print(f"Documented fields: {len(dictionary)}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")

if __name__ == "__main__":
    main()
