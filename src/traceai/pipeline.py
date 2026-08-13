"""Application pipeline joining input, analysis, and reporting boundaries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from traceai.analyzer import RequirementQualityAnalyzer
from traceai.data_loader import load_requirements
from traceai.models import AnalysisReport
from traceai.reporting import build_report, write_report


def run_analysis(
    input_path: Path,
    output_dir: Path,
    *,
    generated_at: datetime | None = None,
) -> tuple[AnalysisReport, tuple[Path, Path]]:
    """Run the complete deterministic Day 1 pipeline."""
    requirements = load_requirements(input_path)
    results = RequirementQualityAnalyzer().analyze_many(requirements)
    report = build_report(results, input_path, generated_at=generated_at)
    output_paths = write_report(report, output_dir)
    return report, output_paths
