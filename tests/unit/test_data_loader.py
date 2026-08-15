"""Unit tests for the CSV input boundary."""

from pathlib import Path

import pytest

from traceai.data_loader import load_requirements
from traceai.exceptions import DataValidationError


def test_loads_versioned_sample_dataset(sample_data_path: Path) -> None:
    requirements = load_requirements(sample_data_path)

    assert len(requirements) == 18
    assert requirements[0].requirement_id == "REQ-001"
    assert requirements[-1].revision == 1


def test_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"

    with pytest.raises(DataValidationError, match="does not exist"):
        load_requirements(missing)


def test_rejects_wrong_schema(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("requirement_id,text,extra\nREQ-001,A valid text,unexpected\n")

    with pytest.raises(DataValidationError) as raised:
        load_requirements(invalid)

    assert "missing columns" in str(raised.value)
    assert "unexpected columns: extra" in str(raised.value)


def test_aggregates_invalid_rows_and_duplicates(tmp_path: Path, sample_data_path: Path) -> None:
    header, first_row = sample_data_path.read_text().splitlines()[:2]
    invalid_row = first_row.replace("REQ-001", "invalid")
    duplicate_row = first_row.replace("REQ-001", "REQ-002")
    csv_path = tmp_path / "requirements.csv"
    csv_path.write_text("\n".join([header, first_row, invalid_row, duplicate_row, duplicate_row]))

    with pytest.raises(DataValidationError) as raised:
        load_requirements(csv_path)

    message = str(raised.value)
    assert "row 3" in message
    assert "row 5: duplicate requirement_id 'REQ-002'" in message


def test_rejects_dataset_without_rows(tmp_path: Path, sample_data_path: Path) -> None:
    header = sample_data_path.read_text().splitlines()[0]
    empty = tmp_path / "empty.csv"
    empty.write_text(header + "\n")

    with pytest.raises(DataValidationError, match="no requirement rows"):
        load_requirements(empty)
