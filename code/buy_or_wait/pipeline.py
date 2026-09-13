"""Thin application composition; sample answers are never inputs."""

from pathlib import Path
from tempfile import TemporaryDirectory

from .domain import Prediction
from .forecast import ForecastPolicy, build_forecast
from .loading import build_context, load_requests
from .normalize import normalize
from .output import write_predictions
from .processing import decide
from .validation import validate_output


def run(request_path: Path, dataset: Path, output: Path,
        policy: ForecastPolicy = ForecastPolicy()) -> tuple[Prediction, ...]:
    root = dataset.resolve().parent
    target = output.resolve()
    if target == root / "output.csv" or target == request_path.resolve() or target.is_relative_to(dataset.resolve()):
        raise ValueError("Development output cannot overwrite input data or final output.csv")
    contexts = tuple(normalize(build_context(dataset, r)) for r in load_requests(request_path))
    predictions = tuple(decide(c, build_forecast(c, policy)) for c in contexts)
    # All requests must succeed before any CSV is written.
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        staged = Path(temporary) / "predictions.csv"
        write_predictions(staged, predictions)
        validate_output(staged, tuple(c.request for c in contexts))
        staged.replace(output)
    return predictions
