"""Typed contracts shared by loaders, processing, and output boundaries."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

REQUEST_COLUMNS = (
    "request_id", "user_id", "request_date", "request_type", "requested_amount",
    "desired_completion_date", "allows_partial_payment", "request_text",
)
OUTPUT_COLUMNS = (
    "request_id", "amount_safe_to_pay", "affordability_status",
    "recommended_payment_method", "payment_plan", "earliest_date_for_full_payment",
    "spending_changes_needed", "decision_explanation",
)


class DataError(ValueError):
    """Malformed or inconsistent supplied data."""


class UnsupportedCase(ValueError):
    """Valid input outside the explicitly supported development slice."""


class Status(str, Enum):
    NOW = "affordable_now"
    PLAN = "affordable_with_plan"
    LATER = "affordable_later"
    NO = "not_affordable"


class Method(str, Enum):
    FULL = "full_payment"
    PARTIAL = "partial_payment"
    INSTALLMENTS = "installments"
    WAIT = "wait"
    NO = "not_recommended"


class CashKind(str, Enum):
    CASH = "cash"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class Source:
    kind: str
    source_id: str


@dataclass(frozen=True)
class Request:
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str


@dataclass(frozen=True)
class Profile:
    user_id: str
    currency: str
    balance: Decimal
    minimum: Decimal
    methods: frozenset[Method]
    protected: frozenset[str]
    reduce_categories: frozenset[str]
    stop_categories: frozenset[str]
    max_installment_months: int | None


@dataclass(frozen=True)
class Event:
    event_id: str
    category: str
    event_type: str
    description: str
    amount: Decimal | None
    currency: str
    direction: str
    event_date: date
    settlement_date: date | None
    status: str
    linked_event_id: str | None
    flexibility: str
    minimum_allowed_amount: Decimal | None
    source: Source

    @property
    def cash_kind(self) -> CashKind:
        return CashKind.INFORMATIONAL if self.direction == "non_cash" else CashKind.CASH


@dataclass(frozen=True)
class PaymentOption:
    option_id: str
    method: Method
    payment_amount: Decimal
    number_of_payments: int
    first_payment_date: date
    frequency_days: int | None
    financing_fee: Decimal
    total: Decimal


@dataclass(frozen=True)
class Evidence:
    source: Source
    request_id: str | None
    related_event_id: str | None


@dataclass(frozen=True)
class ExtractedFact:
    fact_type: str
    value: str | None
    currency: str | None
    effective_date: date | None
    scope: str
    target_event_id: str | None
    related_event_ids: tuple[str, ...]
    category: str | None
    direction: str | None
    confidence: str
    supporting_evidence: str
    source: Source
    provider: str
    model: str
    prompt_version: str
    schema_version: str


@dataclass(frozen=True)
class FxRate:
    settlement_date: date
    from_currency: str
    to_currency: str
    rate: Decimal


@dataclass(frozen=True)
class FinancialContext:
    request: Request
    profile: Profile
    events: tuple[Event, ...]
    options: tuple[PaymentOption, ...]
    evidence: tuple[Evidence, ...]
    rates: tuple[FxRate, ...]
    extracted_facts: tuple[ExtractedFact, ...] = ()


@dataclass(frozen=True)
class Payment:
    date: date
    amount: Decimal


@dataclass(frozen=True)
class SpendingChange:
    action: str
    event_id: str
    new_amount: Decimal | None = None


@dataclass(frozen=True)
class Prediction:
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: Status
    recommended_payment_method: Method
    payment_plan: tuple[Payment, ...]
    earliest_date_for_full_payment: date | None
    spending_changes_needed: tuple[SpendingChange, ...]
    decision_explanation: str
