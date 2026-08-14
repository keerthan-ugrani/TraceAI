"""Integration test crossing CSV, validation, rules, and report boundaries."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from traceai.pipeline import run_analysis


@pytest.mark.integration
def test_complete_sample_pipeline_produces_reproducible_outputs(
    sample_data_path: Path, tmp_path: Path
) -> None:
    timestamp = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

    report, (json_path, csv_path) = run_analysis(
        sample_data_path,
        tmp_path / "outputs",
        generated_at=timestamp,
    )

    persisted = json.loads(json_path.read_text())
    assert persisted == json.loads(report.model_dump_json())
    assert persisted["metadata"]["generated_at"] == "2026-08-12T12:00:00Z"
    assert persisted["summary"]["total_requirements"] == 18
    assert persisted["summary"]["passed"] > 0
    assert persisted["summary"]["high_severity_findings"] > 0
    assert "REQ-001" in csv_path.read_text()
