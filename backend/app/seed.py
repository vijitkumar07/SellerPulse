
"""Reproducible synthetic SellerPulse dataset generator."""

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .database import Base, SessionLocal, engine
from .generator_config import DEFAULT_SEED, get_scale
from .models import (
    Seller,
    ProductListing,
    Order,
    OrderSeller,
    OrderLine,
    Fulfillment,
    CustomerReview,
    Dispute,
    CommissionRule,
    Payout,
    PayoutLine,
    EntityEvent,
)

SEED = DEFAULT_SEED
BASE_TIME = datetime(2026, 10, 22, 12, 0, 0)

GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "ground_truth.json"
)


def chunks(items, size=2000):
    """Yield manageable batches to reduce database memory usage."""
    for start in range(0, len(items), size):
        yield items[start : start + size]


def add_in_batches(db, items, size=2000):
    for batch in chunks(items, size):
        db.add_all(batch)
        db.flush()


def seed_database(scale_name="full", seed=SEED):
    """Regenerate the synthetic database.

    WARNING: This drops all tables in the configured database.
    Use only with the dedicated synthetic development database.
    """
    scale = get_scale(scale_name)
    seller_count = scale.sellers
    listing_count = scale.listings
    order_count = scale.orders
    dispute_count = scale.disputes

    if min(seller_count, listing_count, order_count, dispute_count) <= 0:
        raise ValueError("All dataset sizes must be greater than zero.")

    if order_count < 50 or order_count % 10 != 0:
        raise ValueError(
            "Order count must be at least 50 and divisible by 10."
        )

    if dispute_count != order_count // 10:
        raise ValueError(
            "This generator creates one dispute per 10 orders. "
            "Set disputes to orders // 10 in generator_config.py."
        )

    rng = random.Random(seed)

    anomaly_orders = {
        "payout_before_delivery_or_hold_release": order_count - 40,
        "commission_applied_twice": order_count - 30,
        "dispute_not_deducted": order_count - 10,
        "payout_total_mismatch": order_count,
    }

    anomaly_listing_id = min(50, listing_count)
    anomaly_seller_id = ((anomaly_listing_id - 1) % seller_count) + 1
    reserved_order_ids = set(anomaly_orders.values())

    # Destructive: use only the dedicated synthetic development database.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    ground_truth = {
        "seed": seed,
        "scale": scale_name,
        "description": (
            "Ground-truth labels for synthetic SellerPulse anomaly scenarios. "
            "Labels belong in this file, not in model input features."
        ),
        "anomalies": {
            "payout_before_delivery_or_hold_release": [],
            "commission_applied_twice": [],
            "suspended_seller_listing_active": [anomaly_listing_id],
            "dispute_not_deducted": [],
            "payout_total_mismatch": [],
        },
    }

    db = SessionLocal()

    try:
        # 1. Master data: sellers.
        sellers = []
        seller_business_ids = {}

        for i in range(1, seller_count + 1):
            business_id = f"SELL-{i:06d}"
            seller_business_ids[i] = business_id

            sellers.append(
                Seller(
                    id=i,
                    business_id=business_id,
                    name=f"Seller {i:04d}",
                    status=(
                        "suspended"
                        if i % 50 == 0 or i == anomaly_seller_id
                        else "active"
                    ),
                    created_at=BASE_TIME - timedelta(
                        days=rng.randint(30, 700)
                    ),
                )
            )

        add_in_batches(db, sellers)
        db.flush()

        # 2. Listings: each listing references a valid seller.
        listings = []
        listing_seller = {}
        listing_price = {}
        seller_listing_sequence = defaultdict(int)

        for listing_id in range(1, listing_count + 1):
            seller_id = ((listing_id - 1) % seller_count) + 1
            seller_listing_sequence[seller_id] += 1

            business_id = (
                f"LIST-{seller_business_ids[seller_id]}-"
                f"{seller_listing_sequence[seller_id]:06d}"
            )
            price = round(rng.uniform(10, 500), 2)

            if listing_id == anomaly_listing_id:
                status = "active"
            elif sellers[seller_id - 1].status == "suspended":
                status = "inactive"
            else:
                status = "active"

            listing_seller[listing_id] = seller_id
            listing_price[listing_id] = price

            listings.append(
                ProductListing(
                    id=listing_id,
                    business_id=business_id,
                    seller_id=seller_id,
                    title=f"Product Listing {listing_id:05d}",
                    price=price,
                    status=status,
                )
            )

        add_in_batches(db, listings)
        db.flush()

        # 3. Commission rules with effective dates.
        db.add_all(
            [
                CommissionRule(
                    seller_id=None,
                    rate=0.10,
                    is_active=True,
                    effective_from=datetime(2025, 1, 1),
                    effective_to=None,
                ),
                CommissionRule(
                    seller_id=None,
                    rate=0.12,
                    is_active=False,
                    effective_from=datetime(2024, 1, 1),
                    effective_to=datetime(2024, 12, 31, 23, 59, 59),
                ),
            ]
        )
        db.flush()

        # 4. Orders and child records.
        orders = []
        order_lines = []
        order_sellers = []
        fulfillments = []
        reviews = []
        disputes = []
        events = []

        # Kept for payout calculations without re-querying the database.
        order_seller_gross = defaultdict(float)
        order_line_ids = defaultdict(list)
        order_deliveries = defaultdict(list)
        order_amounts = {}
        order_primary_seller = {}
        order_created = {}
        order_statuses = {}
        resolved_dispute_orders = set()

        line_id = 0
        fulfillment_id = 0
        review_id = 0
        dispute_id = 0
        event_id = 0

        def add_event(entity_type, entity_id, event_type, old, new, when):
            nonlocal event_id
            event_id += 1
            events.append(
                EntityEvent(
                    id=event_id,
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    event_type=event_type,
                    old_value=old,
                    new_value=new,
                    occurred_at=when,
                    details="Generated synthetic lifecycle event",
                )
            )

        for i in range(1, order_count + 1):
            created = BASE_TIME - timedelta(days=rng.randint(1, 180))

            # Two lines for most orders, with different seller ownership
            # where the available listing catalogue permits it.
            line_count = 2 if i % 3 != 0 and listing_count > 1 else 1
            selected_listing_ids = []

            first_listing = ((i - 1) % listing_count) + 1
            selected_listing_ids.append(first_listing)

            if line_count == 2:
                second_listing = ((i * 17 + 6) % listing_count) + 1

                # Prefer a listing owned by another seller.
                if listing_seller[second_listing] == listing_seller[first_listing]:
                    for offset in range(1, listing_count + 1):
                        candidate = ((second_listing - 1 + offset) % listing_count) + 1
                        if (
                            listing_seller[candidate]
                            != listing_seller[first_listing]
                        ):
                            second_listing = candidate
                            break

                selected_listing_ids.append(second_listing)

            status = rng.choice(
                ["delivered", "delivered", "shipped", "processing"]
            )
            if i in reserved_order_ids:
                status = "delivered"

            primary_seller_id = listing_seller[selected_listing_ids[0]]
            order_primary_seller[i] = primary_seller_id
            order_created[i] = created
            order_statuses[i] = status

            current_line_values = []
            sellers_for_order = set()

            for selected_listing in selected_listing_ids:
                line_id += 1
                seller_id = listing_seller[selected_listing]
                quantity = rng.randint(1, 3)
                unit_price = listing_price[selected_listing]
                line_gross = round(quantity * unit_price, 2)

                current_line_values.append(
                    (line_id, selected_listing, seller_id,
                     quantity, unit_price, line_gross)
                )
                sellers_for_order.add(seller_id)
                order_seller_gross[(i, seller_id)] += line_gross
                order_line_ids[i].append(line_id)

            order_total = round(
                sum(item[5] for item in current_line_values), 2
            )
            order_amounts[i] = order_total

            orders.append(
                Order(
                    id=i,
                    business_id=f"ORD-2026-{i:06d}",
                    seller_id=primary_seller_id,
                    status=status,
                    total_amount=order_total,
                    created_at=created,
                )
            )

            for seller_id in sorted(sellers_for_order):
                order_sellers.append(
                    OrderSeller(
                        order_id=i,
                        seller_id=seller_id,
                        created_at=created,
                    )
                )

            for (
                current_line_id,
                selected_listing,
                seller_id,
                quantity,
                unit_price,
                line_gross,
            ) in current_line_values:
                order_lines.append(
                    OrderLine(
                        id=current_line_id,
                        business_id=f"LINE-{current_line_id:08d}",
                        order_id=i,
                        listing_id=selected_listing,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                )

                
                is_late_shipment = i % 25 == 0 and i not in reserved_order_ids
                shipment_delay_hours = 72 if is_late_shipment else 12
                shipped_at = created + timedelta(hours=shipment_delay_hours)

                delivered_at = (
                    shipped_at + timedelta(days=rng.randint(1, 7))
                    if status == "delivered"
                    else None
                )

                fulfillment_id += 1
                fulfillments.append(
                    Fulfillment(
                        id=fulfillment_id,
                        business_id=f"FUL-{current_line_id:08d}",
                        order_id=i,
                        order_line_id=current_line_id,
                        status=status,
                        shipped_at=shipped_at,
                        delivered_at=delivered_at,
                   
                    )
                )
                order_deliveries[i].append(delivered_at)

                add_event(
                    "fulfillment", f"FUL-{current_line_id:08d}",
                    "status_changed", None, "processing", created,
                )
                if status != "processing":
                    add_event(
                        "fulfillment", f"FUL-{current_line_id:08d}",
                        "status_changed", "processing", status, shipped_at,
                    )

            add_event(
                "order", f"ORD-2026-{i:06d}", "order_created",
                None, "created", created,
            )
            if status != "created":
                add_event(
                    "order", f"ORD-2026-{i:06d}", "status_changed",
                    "created", status, created + timedelta(minutes=1),
                )

            if i % 10 == 0:
                review_id += 1
                reviews.append(
                    CustomerReview(
                        id=review_id,
                        order_id=i,
                        rating=rng.randint(1, 5),
                        comment="Synthetic review",
                    )
                )

                if i == anomaly_orders["dispute_not_deducted"]:
                    dispute_status = "resolved"
                elif i in reserved_order_ids:
                    dispute_status = "open"
                else:
                    dispute_status = "open" if i % 20 == 0 else "resolved"

                if dispute_status == "resolved":
                    resolved_dispute_orders.add(i)

                dispute_id += 1
                disputes.append(
                    Dispute(
                        id=dispute_id,
                        business_id=f"DSP-2026-{dispute_id:06d}",
                        order_id=i,
                        amount=round(order_total * 0.10, 2),
                        status=dispute_status,
                        created_at=created + timedelta(days=2),
                    )
                )

                add_event(
                    "dispute", f"DSP-2026-{dispute_id:06d}", "dispute_created",
                    None, "open", created + timedelta(days=2),
                )
                if dispute_status == "resolved":
                    add_event(
                        "dispute", f"DSP-2026-{dispute_id:06d}", "status_changed",
                        "open", "resolved", created + timedelta(days=3),
                    )

        # Parent tables before dependent tables.
        add_in_batches(db, orders)
        add_in_batches(db, order_lines)
        add_in_batches(db, order_sellers)
        add_in_batches(db, fulfillments)
        add_in_batches(db, reviews)
        add_in_batches(db, disputes)
        db.flush()

        # 5. Normal payouts: one payout per eligible order-seller group.
        # Avoid normal payouts on disputed orders so seeded anomalies remain
        # isolated and the detector does not flag unrelated synthetic rows.
        payouts = []
        payout_lines = []
        payout_id = 0
        payout_line_id = 0

        for order_id in range(1, order_count + 1):
            if order_id in reserved_order_ids:
                continue
            if order_statuses[order_id] != "delivered":
                continue
            # Include a deterministic sample of resolved single-line disputes.
            resolved_dispute_sample = (order_id % 30 == 0 and order_id not in reserved_order_ids)
            if order_id % 4 != 0 and not resolved_dispute_sample:
                continue
            if order_id % 10 == 0 and not resolved_dispute_sample:
                continue

            delivered_dates = [
                value for value in order_deliveries[order_id]
                if value is not None
            ]
            if not delivered_dates:
                continue

            latest_delivery = max(delivered_dates)
            hold_release = max(
                order_created[order_id] + timedelta(days=10),
                latest_delivery + timedelta(days=7),
            )

            for seller_id in sorted(
                seller
                for (oid, seller) in order_seller_gross
                if oid == order_id
            ):
                gross = round(order_seller_gross[(order_id, seller_id)], 2)
                commission = round(gross * 0.10, 2)

                # Synthetic refund cases, derived deterministically.
                refund = (
                    round(gross * 0.05, 2)
                    if order_id % 17 == 0
                    else 0.0
                )

                # Reserve retained from a portion of seller transactions.
                reserve = (
                    round(gross * 0.05, 2)
                    if order_id % 7 == 0
                    else 0.0
                )

                # Every selected order divisible by 30 is a resolved, single-line dispute.
                dispute_deduction = round(gross * 0.10, 2) if order_id % 30 == 0 else 0.0
                net = round(
                    gross - commission - refund - reserve
                    - dispute_deduction,
                    2,
                )

                if net < 0:
                    raise ValueError(
                        f"Negative payout calculated for order {order_id}."
                    )

                payout_id += 1
                payout_line_id += 1
                business_payout_id = f"PAYOUT-2026-{payout_id:06d}"

                payouts.append(
                    Payout(
                        id=payout_id,
                        business_id=business_payout_id,
                        seller_id=seller_id,
                        status="paid",
                        total_amount=net,
                        created_at=hold_release,
                        hold_released_at=hold_release,
                    )
                )

                payout_lines.append(
                    PayoutLine(
                        id=payout_line_id,
                        payout_id=payout_id,
                        order_id=order_id,
                        gross_amount=gross,
                        commission_amount=commission,
                        dispute_deduction=dispute_deduction,
                        refund_amount=refund,
                        reserve_amount=reserve,
                        net_amount=net,
                    )
                )

                add_event(
                    "payout",
                    business_payout_id,
                    "payout_created",
                    None,
                    "paid",
                    hold_release,
                )

                if len(payouts) >= 2000:
                    add_in_batches(db, payouts)
                    add_in_batches(db, payout_lines)
                    db.flush()
                    payouts.clear()
                    payout_lines.clear()

        if payouts:
            add_in_batches(db, payouts)
            add_in_batches(db, payout_lines)
            db.flush()

        # 6. Insert five intentional anomalies, with separate ground truth.
        order_by_id = {order.id: order for order in orders}
        fulfillment_by_line = {
            item.order_line_id: item for item in fulfillments
        }

        def add_anomaly_payout(
            scenario,
            order_id,
            *,
            commission_multiplier=1.0,
            dispute_deduction=0.0,
            total_adjustment=0.0,
            early_payout=False,
        ):
            nonlocal payout_id, payout_line_id

            order = order_by_id[order_id]
            seller_id = order_primary_seller[order_id]
            gross = round(order_amounts[order_id], 2)
            commission = round(gross * 0.10 * commission_multiplier, 2)
            deduction = round(dispute_deduction, 2)

            refund = 0.0
            reserve = 0.0
            net = round(
                gross - commission - deduction - refund - reserve, 2
            )

            if early_payout:
                for current_line_id in order_line_ids[order_id]:
                    fulfillment = fulfillment_by_line[current_line_id]
                    fulfillment.delivered_at = None
                    fulfillment.status = "shipped"
                order.status = "shipped"
                created_at = BASE_TIME
                hold_released_at = None
            else:
                created_at = BASE_TIME + timedelta(days=1)
                hold_released_at = created_at

            payout_id += 1
            payout_line_id += 1
            business_payout_id = f"PAYOUT-2026-{payout_id:06d}"

            db.add(
                Payout(
                    id=payout_id,
                    business_id=business_payout_id,
                    seller_id=seller_id,
                    status="paid",
                    total_amount=round(net + total_adjustment, 2),
                    created_at=created_at,
                    hold_released_at=hold_released_at,
                )
            )

            db.add(
                PayoutLine(
                    id=payout_line_id,
                    payout_id=payout_id,
                    order_id=order_id,
                    gross_amount=gross,
                    commission_amount=commission,
                    dispute_deduction=deduction,
                    refund_amount=refund,
                    reserve_amount=reserve,
                    net_amount=net,
                )
            )

            ground_truth["anomalies"][scenario].append(payout_id)

            add_event(
                "payout",
                business_payout_id,
                "payout_created",
                None,
                "paid",
                created_at,
            )

        add_anomaly_payout(
            "payout_before_delivery_or_hold_release",
            anomaly_orders["payout_before_delivery_or_hold_release"],
            early_payout=True,
        )

        add_anomaly_payout(
            "commission_applied_twice",
            anomaly_orders["commission_applied_twice"],
            commission_multiplier=2.0,
        )

        add_anomaly_payout(
            "dispute_not_deducted",
            anomaly_orders["dispute_not_deducted"],
            dispute_deduction=0.0,
        )

        add_anomaly_payout(
            "payout_total_mismatch",
            anomaly_orders["payout_total_mismatch"],
            total_adjustment=25.00,
        )

        add_in_batches(db, events)
        db.commit()

        GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        GROUND_TRUTH_PATH.write_text(
            json.dumps(ground_truth, indent=2),
            encoding="utf-8",
        )

        print("Synthetic database seeded successfully.")
        print(f"Seed: {seed}")
        print(f"Scale: {scale_name}")
        print(f"Sellers: {db.query(Seller).count():,}")
        print(f"Listings: {db.query(ProductListing).count():,}")
        print(f"Orders: {db.query(Order).count():,}")
        print(f"Order lines: {db.query(OrderLine).count():,}")
        print(f"Order-seller links: {db.query(OrderSeller).count():,}")
        print(f"Fulfillments: {db.query(Fulfillment).count():,}")
        print(f"Reviews: {db.query(CustomerReview).count():,}")
        print(f"Disputes: {db.query(Dispute).count():,}")
        print(f"Commission rules: {db.query(CommissionRule).count():,}")
        print(f"Payouts: {db.query(Payout).count():,}")
        print(f"Payout lines: {db.query(PayoutLine).count():,}")
        print(f"Entity events: {db.query(EntityEvent).count():,}")
        print(f"Ground truth: {GROUND_TRUTH_PATH}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic SellerPulse data."
    )
    parser.add_argument(
        "--scale",
        choices=("starter", "full"),
        default="full",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    seed_database(scale_name=args.scale, seed=args.seed)
