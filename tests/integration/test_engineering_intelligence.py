"""Integration coverage from local persistence through validated advisory output."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_loader import load_engineering_dataset
from traceai.engineering_reporting import write_engineering_report
from traceai.intelligence import EngineeringIntelligenceService


@pytest.mark.integration
def test_requirement_id_to_complete_engineering_intelligence_report(
    engineering_data_path: Path, tmp_path: Path
) -> None:
    service = EngineeringIntelligenceService(
        EngineeringGraph(load_engineering_dataset(engineering_data_path))
    )

    report = service.analyze_requirement(
        "SWE-REQ-014",
        release_id="REL-1.4.0",
        change_request_id="CR-091",
        generated_at=datetime(2026, 8, 13, 8, 0, tzinfo=UTC),
    )
    output = write_engineering_report(report, tmp_path / "report.json")
    persisted = json.loads(output.read_text())

    assert report.overall_health == "BLOCKED"
    assert report.failure_analysis.first_failure_id == "IT-045"
    assert report.release_eligibility.status == "BLOCKED"
    assert report.root_cause_analysis.confidence == "High"
    assert report.change_impact is not None
    assert persisted == json.loads(report.model_dump_json())
