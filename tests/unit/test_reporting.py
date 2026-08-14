"""Unit tests for report aggregation and persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path

from traceai.models import Finding, QualityStatus, RequirementAnalysis, Severity
from traceai.reporting import build_report, write_report


def _results() -> list[RequirementAnalysis]:
    return [
        RequirementAnalysis(
            requirement_id="REQ-001",
            quality_score=100,
            quality_status=QualityStatus.PASS,
            findings=[],
        ),
        RequirementAnalysis(
            requirement_id="REQ-002",
            quality_score=75,
            quality_status=QualityStatus.REVIEW,
            findings=[
                Finding(
                    rule_id="RQ-AMB-001",
                    severity=Severity.HIGH,
                    message="Ambiguous",
                    evidence="quickly",
                    recommendation="Add a limit",
                )
            ],
        ),
    ]


def test_build_report_aggregates_results() -> None:
    timestamp = datetime(2026, 8, 12, tzinfo=UTC)

    report = build_report(_results(), Path("requirements.csv"), generated_at=timestamp)

    assert report.metadata.generated_at == timestamp
    assert report.summary.total_requirements == 2
    assert report.summary.passed == 1
    assert report.summary.review_required == 1
    assert report.summary.high_severity_findings == 1


def test_write_report_persists_json_and_flat_csv(tmp_path: Path) -> None:
    report = build_report(_results(), Path("requirements.csv"))

    json_path, csv_path = write_report(report, tmp_path / "nested")

    data = json.loads(json_path.read_text())
    assert data["summary"]["total_requirements"] == 2
    csv_content = csv_path.read_text()
    assert "REQ-001,100,PASS" in csv_content
    assert "RQ-AMB-001,HIGH" in csv_content
