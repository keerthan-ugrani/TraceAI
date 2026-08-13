"""Atomic persistence of complete Engineering Intelligence reports."""

from __future__ import annotations

from pathlib import Path

from traceai.engineering_models import EngineeringIntelligenceReport
from traceai.reporting import _atomic_write


def write_engineering_report(report: EngineeringIntelligenceReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(output_path, report.model_dump_json(indent=2) + "\n")
    return output_path
