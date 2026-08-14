"""Unit tests for the validated graph persistence boundary."""

import json
from pathlib import Path

import pytest

from traceai.engineering_loader import load_engineering_dataset
from traceai.exceptions import DataValidationError


def test_loads_complete_synthetic_engineering_dataset(engineering_data_path: Path) -> None:
    dataset = load_engineering_dataset(engineering_data_path)

    assert dataset.metadata["hero_requirement_id"] == "SWE-REQ-014"
    assert len(dataset.artifacts) == 49
    assert len(dataset.relationships) == 58


def test_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{")

    with pytest.raises(DataValidationError, match="not valid JSON"):
        load_engineering_dataset(path)


def test_rejects_dangling_relationship(tmp_path: Path, engineering_data_path: Path) -> None:
    payload = json.loads(engineering_data_path.read_text())
    payload["relationships"][0]["target_id"] = "MISSING-001"
    path = tmp_path / "dangling.json"
    path.write_text(json.dumps(payload))

    with pytest.raises(DataValidationError, match="unknown artifacts"):
        load_engineering_dataset(path)


def test_rejects_duplicate_artifact_id(tmp_path: Path, engineering_data_path: Path) -> None:
    payload = json.loads(engineering_data_path.read_text())
    payload["artifacts"].append(payload["artifacts"][0])
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(payload))

    with pytest.raises(DataValidationError, match="duplicate artifact IDs"):
        load_engineering_dataset(path)
