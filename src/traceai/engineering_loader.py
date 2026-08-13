"""Persistence adapter for validated engineering graph data."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from traceai.engineering_models import EngineeringDataset
from traceai.exceptions import DataValidationError


def load_engineering_dataset(path: Path) -> EngineeringDataset:
    """Load a standalone demo dataset and reject malformed graph references."""
    if not path.is_file():
        raise DataValidationError(f"Engineering dataset does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return EngineeringDataset.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"Engineering dataset is not valid JSON: {exc}") from exc
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise DataValidationError(f"Engineering dataset validation failed: {details}") from exc
