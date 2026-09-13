"""Answer separation belongs to evaluation, not the application."""

import csv
from dataclasses import dataclass
from pathlib import Path

from buy_or_wait.domain import OUTPUT_COLUMNS, REQUEST_COLUMNS

SMOKE_SUBSETS = {"smoke": ("request_09", "request_01")}


@dataclass(frozen=True)
class Sample:
    inputs: dict[str, str]
    expected: dict[str, str]


def load_samples(path: Path) -> tuple[Sample, ...]:
    samples = []
    seen = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUEST_COLUMNS + OUTPUT_COLUMNS[1:]:
            raise ValueError("Unexpected sample schema")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Malformed sample row")
            rid = row["request_id"]
            if not rid or rid in seen:
                raise ValueError("Missing or duplicate sample ID")
            seen.add(rid)
            # Separate dictionaries before a request can reach application code.
            samples.append(Sample({k: row[k] for k in REQUEST_COLUMNS},
                                  {k: row[k] for k in OUTPUT_COLUMNS}))
    return tuple(samples)


def select_samples(samples: tuple[Sample, ...], request_ids: tuple[str, ...] = (),
                   subset: str | None = None, all_samples: bool = False) -> tuple[Sample, ...]:
    if sum((bool(request_ids), subset is not None, all_samples)) != 1:
        raise ValueError("Select explicit IDs, a named subset, or all samples")
    if all_samples:
        return samples
    if subset is not None:
        if subset not in SMOKE_SUBSETS:
            raise ValueError(f"Unknown subset: {subset}")
        request_ids = SMOKE_SUBSETS[subset]
    if len(request_ids) != len(set(request_ids)):
        raise ValueError("Duplicate selected request IDs")
    by_id = {s.inputs["request_id"]: s for s in samples}
    unknown = set(request_ids) - set(by_id)
    if unknown:
        raise ValueError(f"Unknown sample IDs: {sorted(unknown)}")
    return tuple(by_id[rid] for rid in request_ids)


def write_input(path: Path, inputs: dict[str, str]) -> None:
    if set(inputs) != set(REQUEST_COLUMNS):
        raise ValueError("Only input fields may cross the application boundary")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REQUEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(inputs)
