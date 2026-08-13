"""Report assembly and atomic JSON/CSV persistence."""

from __future__ import annotations

import csv
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from traceai import __version__
from traceai.models import (
    AnalysisReport,
    QualityStatus,
    ReportMetadata,
    ReportSummary,
    RequirementAnalysis,
    Severity,
)


def build_report(
    results: list[RequirementAnalysis],
    source_file: Path,
    *,
    generated_at: datetime | None = None,
) -> AnalysisReport:
    """Create a versioned report from individual analysis results."""
    status_counts = Counter(result.quality_status for result in results)
    severity_counts = Counter(finding.severity for result in results for finding in result.findings)
    summary = ReportSummary(
        total_requirements=len(results),
        passed=status_counts[QualityStatus.PASS],
        review_required=status_counts[QualityStatus.REVIEW],
        failed=status_counts[QualityStatus.FAIL],
        requirements_with_findings=sum(bool(result.findings) for result in results),
        high_severity_findings=severity_counts[Severity.HIGH],
        medium_severity_findings=severity_counts[Severity.MEDIUM],
        low_severity_findings=severity_counts[Severity.LOW],
    )
    return AnalysisReport(
        metadata=ReportMetadata(
            analyzer_version=__version__,
            source_file=str(source_file),
            generated_at=generated_at or datetime.now(UTC),
        ),
        summary=summary,
        results=results,
    )


def write_report(report: AnalysisReport, output_dir: Path) -> tuple[Path, Path]:
    """Atomically write machine-readable JSON and analyst-friendly CSV outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "analysis_report.json"
    csv_path = output_dir / "requirements_findings.csv"

    _atomic_write(json_path, report.model_dump_json(indent=2) + "\n")
    _atomic_write(csv_path, _findings_csv(report))
    return json_path, csv_path


def _findings_csv(report: AnalysisReport) -> str:
    output = StringIO(newline="")
    fieldnames = [
        "requirement_id",
        "quality_score",
        "quality_status",
        "rule_id",
        "severity",
        "message",
        "evidence",
        "recommendation",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for result in report.results:
        if not result.findings:
            writer.writerow(
                {
                    "requirement_id": result.requirement_id,
                    "quality_score": result.quality_score,
                    "quality_status": result.quality_status,
                }
            )
            continue
        for finding in result.findings:
            writer.writerow(
                {
                    "requirement_id": result.requirement_id,
                    "quality_score": result.quality_score,
                    "quality_status": result.quality_status,
                    "rule_id": finding.rule_id,
                    "severity": finding.severity,
                    "message": finding.message,
                    "evidence": finding.evidence or "",
                    "recommendation": finding.recommendation,
                }
            )
    return output.getvalue()


def _atomic_write(path: Path, content: str) -> None:
    """Replace a report only after its complete content is safely written."""
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise
