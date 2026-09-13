"""Compatibility entry point for deterministic planning."""

from .domain import FinancialContext, Prediction
from .forecast import ForecastTimeline
from .planning import plan


def decide(context: FinancialContext, timeline: ForecastTimeline) -> Prediction:
    return plan(context, timeline).prediction
