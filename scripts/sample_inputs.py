"""Benchmark-side projection boundary, deliberately outside application code.

Read only input-column positions. Expected output values are discarded before
any request is passed to the application. This is not an evaluator.
"""

import csv
from pathlib import Path

INPUT_COLUMNS = (
    "request_id", "user_id", "request_date", "request_type", "requested_amount",
    "desired_completion_date", "allows_partial_payment", "request_text",
)


def prepare_inputs(sample_path: Path, destination: Path, request_ids: tuple[str, ...]) -> None:
    if not request_ids or len(set(request_ids)) != len(request_ids):
        raise ValueError("Choose distinct sample IDs")
    if destination.resolve() == sample_path.resolve():
        raise ValueError("Cannot overwrite sample data")
    selected = {}
    with sample_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)) or not set(INPUT_COLUMNS) <= set(header):
            raise ValueError("Malformed sample input header")
        indexes = [header.index(column) for column in INPUT_COLUMNS]
        seen = set()
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Malformed sample row")
            # Never build or pass a combined input/answer mapping.
            values = tuple(row[index] for index in indexes)
            rid = values[0]
            if not rid or rid in seen:
                raise ValueError("Missing or duplicate sample ID")
            seen.add(rid)
            if rid in request_ids:
                selected[rid] = values
    if set(selected) != set(request_ids):
        raise ValueError(f"Unknown sample IDs: {sorted(set(request_ids) - set(selected))}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(INPUT_COLUMNS)
        writer.writerows(selected[rid] for rid in request_ids)
