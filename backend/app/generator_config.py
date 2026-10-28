
"""Configuration for reproducible SellerPulse data generation."""

from dataclasses import dataclass

DEFAULT_SEED = 20261022


@dataclass(frozen=True)
class DatasetScale:
    sellers: int
    listings: int
    orders: int
    disputes: int


SCALES = {
    "starter": DatasetScale(
        sellers=20,
        listings=100,
        orders=500,
        disputes=50,
    ),
    "full": DatasetScale(
        sellers=2_000,
        listings=20_000,
        orders=100_000,
        disputes=10_000,
    ),
}


def get_scale(name: str) -> DatasetScale:
    """Get dataset sizes for starter or full generation."""
    try:
        return SCALES[name.lower()]
    except KeyError:
        valid = ", ".join(SCALES)
        raise ValueError(
            f"Unknown scale '{name}'. Choose one of: {valid}"
        ) from None
