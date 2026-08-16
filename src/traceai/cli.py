"""Dependency-light command-line interface for local and CI execution."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_loader import load_engineering_dataset
from traceai.engineering_reporting import write_engineering_report
from traceai.exceptions import TraceAIError
from traceai.intelligence import EngineeringIntelligenceService


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser separately so its behavior is unit-testable."""
    parser = argparse.ArgumentParser(
        prog="traceai",
        description="Analyze engineering requirement quality without modifying source artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a requirements CSV file")
    analyze.add_argument("--input", type=Path, required=True, help="Path to requirements CSV")
    analyze.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for JSON and CSV reports (default: outputs)",
    )
    analyze.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Return exit code 2 when high-severity findings exist",
    )

    trace = subparsers.add_parser(
        "trace", help="Analyze one Requirement ID across the complete engineering digital thread"
    )
    trace.add_argument("requirement_id", help="Controlled software requirement ID")
    trace.add_argument(
        "--data",
        type=Path,
        default=Path("data/engineering_data.json"),
        help="Validated engineering dataset",
    )
    trace.add_argument("--release-id", help="Release to evaluate; defaults to demo release")
    trace.add_argument("--change-request-id", help="Change request to analyze")
    trace.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/engineering_intelligence_report.json"),
        help="JSON evidence report path",
    )
    from traceai.ai_cli import add_ai_parser

    add_ai_parser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI and translate expected failures into stable exit codes."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "trace":
            _run_trace_command(args)
            return
        if args.command == "ai":
            from traceai.ai_cli import run_ai_command

            run_ai_command(args)
            return
        from traceai.pipeline import run_analysis

        report, output_paths = run_analysis(args.input, args.output_dir)
    except TraceAIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    summary = report.summary
    print(f"Analyzed {summary.total_requirements} requirements")
    print(
        f"PASS={summary.passed} REVIEW={summary.review_required} FAIL={summary.failed} "
        f"HIGH_FINDINGS={summary.high_severity_findings}"
    )
    for output_path in output_paths:
        print(f"Wrote {output_path}")

    if args.fail_on_high and summary.high_severity_findings:
        raise SystemExit(2)


def _run_trace_command(args: argparse.Namespace) -> None:
    dataset = load_engineering_dataset(args.data)
    service = EngineeringIntelligenceService(EngineeringGraph(dataset))
    report = service.analyze_requirement(
        args.requirement_id,
        release_id=args.release_id,
        change_request_id=args.change_request_id,
        generated_at=datetime.now(UTC),
    )
    output_path = write_engineering_report(report, args.output)
    print("ENGINEERING INTELLIGENCE REPORT")
    print(f"Requirement: {report.requirement.artifact_id} v{report.requirement.version}")
    print(f"Overall: {report.overall_health}")
    print(f"Traceability: {report.metrics.overall_coverage_percent:.1f}%")
    print(f"Verification: {report.metrics.verification_percent:.1f}%")
    print(f"Configuration mismatches: {len(report.configuration_mismatches)}")
    print(f"First failure: {report.failure_analysis.first_failure_id or 'None'}")
    print(f"Release {report.release_eligibility.release_id}: {report.release_eligibility.status}")
    print(f"Probable root cause: {report.root_cause_analysis.probable_root_cause}")
    print(f"Wrote {output_path}")
