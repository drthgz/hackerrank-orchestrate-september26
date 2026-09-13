"""Exact provided settlement-date conversion; never interpolate or fetch rates."""

from datetime import date
from decimal import Decimal

from .domain import FxRate, UnsupportedCase


def to_home(amount: Decimal, currency: str, home: str, settlement_date: date,
            rates: tuple[FxRate, ...]) -> tuple[Decimal, tuple[str, ...]]:
    if currency == home:
        return amount, ()
    matches = [r for r in rates if (r.settlement_date, r.from_currency, r.to_currency) == (settlement_date, currency, home)]
    if len(matches) != 1:
        raise UnsupportedCase(f"Exactly one supplied FX rate required: {settlement_date} {currency}->{home}")
    return amount * matches[0].rate, (f"fx:{settlement_date}:{currency}:{home}",)
