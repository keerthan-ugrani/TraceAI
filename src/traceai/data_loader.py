"""Input boundary for validated CSV requirements."""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import ValidationError

from traceai.exceptions import DataValidationError
from traceai.models import Requirement

EXPECTED_COLUMNS = {
    "requirement_id",
    "title",
    "text",
    "component",
    "classification",
    "status",
    "verification_method",
    "source",
    "revision",
}


def load_requirements(path: Path) -> list[Requirement]:
    """Load and validate a CSV file, reporting all invalid rows together."""
    if not path.is_file():
        raise DataValidationError(f"Requirements file does not exist: {path}")

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_columns = set(reader.fieldnames or [])
        missing_columns = EXPECTED_COLUMNS - actual_columns
        unexpected_columns = actual_columns - EXPECTED_COLUMNS

        if missing_columns or unexpected_columns:
            details: list[str] = []
            if missing_columns:
                details.append(f"missing columns: {', '.join(sorted(missing_columns))}")
            if unexpected_columns:
                details.append(f"unexpected columns: {', '.join(sorted(unexpected_columns))}")
            raise DataValidationError("Invalid CSV schema; " + "; ".join(details))

        requirements: list[Requirement] = []
        errors: list[str] = []
        seen_ids: set[str] = set()

        for row_number, row in enumerate(reader, start=2):
            try:
                requirement = Requirement.model_validate(row)
                if requirement.requirement_id in seen_ids:
                    errors.append(
                        f"row {row_number}: duplicate requirement_id '{requirement.requirement_id}'"
                    )
                    continue
                seen_ids.add(requirement.requirement_id)
                requirements.append(requirement)
            except ValidationError as exc:
                messages = "; ".join(
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors()
                )
                errors.append(f"row {row_number}: {messages}")

    if errors:
        raise DataValidationError("Dataset validation failed:\n- " + "\n- ".join(errors))
    if not requirements:
        raise DataValidationError("Dataset contains no requirement rows")

    return requirements
