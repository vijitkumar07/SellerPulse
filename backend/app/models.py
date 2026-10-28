
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)


class ProductListing(Base):
    __tablename__ = "product_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(60), unique=True, nullable=True
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_listing_price_nonnegative"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )

    # Kept for backward compatibility. For multi-seller orders,
    # OrderSeller is the authoritative seller relationship.
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("sellers.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="ck_order_total_nonnegative"
        ),
    )


class OrderSeller(Base):
    """Bridge table: one order can involve multiple sellers."""

    __tablename__ = "order_sellers"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), primary_key=True
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id"), primary_key=True
    )
    created_at: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        Index("ix_order_sellers_seller_id", "seller_id"),
    )


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(60), unique=True, nullable=True
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("product_listings.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="ck_order_line_quantity_positive"
        ),
        CheckConstraint(
            "unit_price >= 0", name="ck_order_line_price_nonnegative"
        ),
        Index("ix_order_lines_order_id", "order_id"),
    )


class Fulfillment(Base):
    __tablename__ = "fulfillments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(80), unique=True, nullable=True
    )

    # Retained for existing API compatibility.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )

    # New line-level relationship enables split fulfillment.
    order_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_lines.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    shipped_at: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )
    delivered_at: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        Index("ix_fulfillments_order_id", "order_id"),
        Index("ix_fulfillments_order_line_id", "order_line_id"),
    )


class CustomerReview(Base):
    __tablename__ = "customer_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )

    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5", name="ck_review_rating"
        ),
    )


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "amount >= 0", name="ck_dispute_amount_nonnegative"
        ),
    )


class CommissionRule(Base):
    __tablename__ = "commission_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("sellers.id"), nullable=True
    )
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Inclusive start; nullable end means no scheduled end.
    effective_from: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )
    effective_to: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "rate >= 0 AND rate <= 1", name="ck_commission_rate_range"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="ck_commission_effective_dates",
        ),
    )


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[str | None] = mapped_column(
        String(40), unique=True, nullable=True
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    hold_released_at: Mapped[DateTime | None] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="ck_payout_total_nonnegative"
        ),
    )


class PayoutLine(Base):
    __tablename__ = "payout_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payout_id: Mapped[int] = mapped_column(
        ForeignKey("payouts.id"), nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False
    )
    gross_amount: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    dispute_deduction: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    refund_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    reserve_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    net_amount: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "payout_id", "order_id", name="uq_payout_order"
        ),
        CheckConstraint(
            "gross_amount >= 0", name="ck_payout_gross"
        ),
        CheckConstraint(
            "commission_amount >= 0", name="ck_payout_commission"
        ),
        CheckConstraint(
            "dispute_deduction >= 0", name="ck_payout_dispute"
        ),
        CheckConstraint(
            "refund_amount >= 0", name="ck_payout_refund"
        ),
        CheckConstraint(
            "reserve_amount >= 0", name="ck_payout_reserve"
        ),
        CheckConstraint(
            "net_amount >= 0", name="ck_payout_net"
        ),
    )


class EntityEvent(Base):
    """Append-only history of entity lifecycle and status changes."""

    __tablename__ = "entity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    old_value: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    new_value: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    occurred_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False
    )
    details: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    __table_args__ = (
        Index("ix_entity_events_entity", "entity_type", "entity_id"),
        Index("ix_entity_events_occurred_at", "occurred_at"),
    )
