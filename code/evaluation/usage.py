"""Measured usage interface; no synthetic calls, costs, or cache activity."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ModelUsage:
    provider: str
    model: str
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    estimated_cost: Decimal | None = None

    def __post_init__(self):
        if not self.provider or not self.model:
            raise ValueError("Usage needs provider and model")
        for name in ("model_calls", "input_tokens", "output_tokens", "retries", "cache_hits", "cache_misses"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 0:
                raise ValueError("Usage counters must be nonnegative integers")
        if self.estimated_cost is not None and (not self.estimated_cost.is_finite() or self.estimated_cost < 0):
            raise ValueError("Invalid estimated cost")


@dataclass
class UsageLedger:
    records: list[ModelUsage] = field(default_factory=list)

    def record(self, usage: ModelUsage) -> None:
        self.records.append(usage)

    def to_dict(self) -> dict:
        counters = ("model_calls", "input_tokens", "output_tokens", "retries", "cache_hits", "cache_misses")
        totals = {name: sum(getattr(r, name) for r in self.records) for name in counters}
        cost = None if any(r.estimated_cost is None for r in self.records) else sum((r.estimated_cost for r in self.records), Decimal("0"))
        totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
        totals["estimated_cost"] = format(cost, "f") if cost is not None else None
        return {"records": [{"provider": r.provider, "model": r.model, **{name: getattr(r, name) for name in counters},
                              "estimated_cost": format(r.estimated_cost, "f") if r.estimated_cost is not None else None} for r in self.records],
                "totals": totals, "note": "Counters are measured per extraction request; unavailable costs remain null."}
