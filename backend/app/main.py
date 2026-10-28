
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .database import get_db
from .detector import detect_anomalies
from .models import (
    Seller,
    ProductListing,
    Order,
    Fulfillment,
    Dispute,
    CommissionRule,
    Payout,
    PayoutLine,
)

app = FastAPI(title="SellerPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def page_result(query, skip: int, limit: int):
    total = query.order_by(None).count()
    items = query.offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
        "data_mode": "synthetic_database",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "sellers": db.query(Seller).count(),
        "active_sellers": db.query(Seller).filter_by(status="active").count(),
        "listings": db.query(ProductListing).count(),
        "orders": db.query(Order).count(),
        "disputes": db.query(Dispute).count(),
        "detected_anomalies": len(detect_anomalies(db)),
        "data_mode": "synthetic_database",
    }


@app.get("/api/anomalies")
def anomalies(db: Session = Depends(get_db)):
    items = detect_anomalies(db)
    return {
        "count": len(items),
        "items": items,
        "data_mode": "synthetic_database",
    }


@app.get("/api/sellers")
def sellers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Seller)

    if q.strip():
        query = query.filter(
            or_(
                Seller.name.ilike(f"%{q.strip()}%"),
                func.cast(Seller.id, str).ilike(f"%{q.strip()}%"),
            )
        )
    if status:
        query = query.filter(Seller.status == status)

    return page_result(query.order_by(Seller.id), skip, limit)


@app.get("/api/listings")
def listings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProductListing)

    if q.strip():
        query = query.filter(
            or_(
                ProductListing.title.ilike(f"%{q.strip()}%"),
                func.cast(ProductListing.id, str).ilike(f"%{q.strip()}%"),
            )
        )
    if status:
        query = query.filter(ProductListing.status == status)

    return page_result(query.order_by(ProductListing.id), skip, limit)


@app.get("/api/orders")
def orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str = "",
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Order)

    if q.strip():
        query = query.filter(
            or_(
                func.cast(Order.id, str).ilike(f"%{q.strip()}%"),
                func.cast(Order.seller_id, str).ilike(f"%{q.strip()}%"),
            )
        )
    if status:
        query = query.filter(Order.status == status)

    return page_result(query.order_by(Order.id), skip, limit)


@app.get("/api/fulfillments")
def fulfillments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Fulfillment)

    if status:
        query = query.filter(Fulfillment.status == status)

    return page_result(query.order_by(Fulfillment.id), skip, limit)


@app.get("/api/disputes")
def disputes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Dispute)

    if status:
        query = query.filter(Dispute.status == status)

    return page_result(query.order_by(Dispute.id), skip, limit)


@app.get("/api/commissions")
def commissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(CommissionRule)
    return page_result(query.order_by(CommissionRule.id), skip, limit)


@app.get("/api/payouts")
def payouts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    line_counts = (
        db.query(
            PayoutLine.payout_id.label("payout_id"),
            func.count(PayoutLine.id).label("line_count"),
        )
        .group_by(PayoutLine.payout_id)
        .subquery()
    )

    query = (
        db.query(
            Payout.id.label("id"),
            Payout.seller_id.label("seller_id"),
            Payout.status.label("status"),
            Payout.total_amount.label("total_amount"),
            Payout.created_at.label("created_at"),
            Payout.hold_released_at.label("hold_released_at"),
            func.coalesce(line_counts.c.line_count, 0).label("line_count"),
        )
        .outerjoin(line_counts, Payout.id == line_counts.c.payout_id)
    )

    if status:
        query = query.filter(Payout.status == status)

    total = query.order_by(None).count()
    rows = (
        query.order_by(Payout.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [dict(row._mapping) for row in rows],
        "data_mode": "synthetic_database",
    }
