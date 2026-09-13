"""Small JSON sidecars for reconciliation and forecast provenance; no labels."""

import json
from dataclasses import asdict
from pathlib import Path


def write_diagnostic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=str, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconciliation_diagnostic(path: Path, resolved) -> None:
    write_diagnostic(path, {"request_id": resolved.context.request.request_id,
                           "event_treatments": [asdict(t) for t in resolved.treatments],
                           "stream_ends": [asdict(t) for t in resolved.stream_ends],
                           "reservation_releases": [asdict(t) for t in resolved.reservation_releases]})
