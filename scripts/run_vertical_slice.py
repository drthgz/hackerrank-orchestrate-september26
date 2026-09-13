"""Development adapter: sample input projection -> isolated application process."""

import argparse
from pathlib import Path
import subprocess
import sys

from sample_inputs import prepare_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-id", action="append", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run_dir = root / "artifacts" / "vertical-slice" / "__".join(args.request_id)
    input_path = run_dir / "requests.csv"
    if len(args.request_id) > 2:
        parser.error("This milestone processes at most two selected samples")
    try:
        prepare_inputs(root / "dataset" / "sample_requests.csv", input_path, tuple(args.request_id))
    except ValueError as exc:
        parser.error(str(exc))
    result = subprocess.run([sys.executable, "-B", str(root / "code" / "main.py"),
                             "--requests", str(input_path), "--output", str(run_dir / "predictions.csv")], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
