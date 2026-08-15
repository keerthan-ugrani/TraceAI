"""Acceptance tests mapped one-to-one to internal TraceAI software requirements."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from traceai.change_impact import ChangeImpactService
from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.failure_analysis import FailureAnalysisService
from traceai.intelligence import EngineeringIntelligenceService
from traceai.pipeline import run_analysis
from traceai.reasoning import DeterministicReasoningFallback
from traceai.release import ReleaseEligibilityEngine
from traceai.traceability import TraceabilityEngine


@pytest.mark.verification
def test_poc_swr_001_full_bidirectional_requirement_trace(
    engineering_graph: EngineeringGraph,
) -> None:
    report = EngineeringIntelligenceService(engineering_graph).analyze_requirement("SWE-REQ-014")
    ids = {step.artifact_id for step in report.digital_thread}

    assert {"SYS-REQ-004", "SWE-REQ-014", "BUILD-158", "REL-1.4.0"} <= ids
    assert "REL-1.5.0" not in ids


@pytest.mark.verification
def test_poc_swr_002_reports_typed_missing_links(
    engineering_graph: EngineeringGraph,
) -> None:
    report = EngineeringIntelligenceService(engineering_graph).analyze_requirement("SWE-REQ-014")
    gap = next(item for item in report.missing_links if item.artifact_id == "SW-UNIT-009")

    assert gap.category == "TRACEABILITY_GAP"
    assert gap.evidence_ids == ["SW-UNIT-009"]


@pytest.mark.verification
def test_poc_swr_003_detects_three_configuration_mismatches(
    engineering_graph: EngineeringGraph,
) -> None:
    mismatches = ConfigurationEngine(engineering_graph).find_mismatches("SWE-REQ-014")

    assert len(mismatches) == 3
    assert any(item.artifact_id == "ARCH-IF-006" for item in mismatches)


@pytest.mark.verification
def test_poc_swr_004_identifies_first_failed_verification(
    engineering_graph: EngineeringGraph,
) -> None:
    result = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")

    assert result.first_failure_id == "IT-045"
    assert result.failure_level == "Integration Verification (SWE.5)"


@pytest.mark.verification
def test_poc_swr_005_calculates_downstream_impact_without_mutation(
    engineering_graph: EngineeringGraph,
) -> None:
    persisted_status = engineering_graph.artifact("BUILD-158").status
    result = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")

    assert result.propagated_statuses["BUILD-158"] == "NOT_RELEASE_ELIGIBLE"
    assert engineering_graph.artifact("BUILD-158").status == persisted_status


@pytest.mark.verification
def test_poc_swr_006_grounds_advisory_rca_in_evidence(
    engineering_graph: EngineeringGraph,
) -> None:
    rca = (
        EngineeringIntelligenceService(engineering_graph)
        .analyze_requirement("SWE-REQ-014")
        .root_cause_analysis
    )

    assert {"IT-045", "ARCH-IF-006"} <= set(rca.evidence_ids)
    assert rca.review_decision == "PROPOSED"


@pytest.mark.verification
def test_poc_swr_007_groups_change_impact_and_stale_artifacts(
    engineering_graph: EngineeringGraph,
) -> None:
    impact = ChangeImpactService(engineering_graph, TraceabilityEngine(engineering_graph)).analyze(
        "CR-091"
    )

    assert "SW-UNIT-007" in impact.affected_by_type["SOFTWARE_UNIT"]
    assert "SW-UNIT-008" in impact.stale_artifact_ids


@pytest.mark.verification
def test_poc_swr_008_applies_deterministic_release_policy(
    engineering_graph: EngineeringGraph,
) -> None:
    traceability = TraceabilityEngine(engineering_graph)
    configuration = ConfigurationEngine(engineering_graph)
    engine = ReleaseEligibilityEngine(engineering_graph, traceability, configuration)

    assert engine.evaluate("SWE-REQ-014", "REL-1.4.0").status == "BLOCKED"
    assert engine.evaluate("SWE-REQ-030", "REL-1.5.0").status == "ELIGIBLE"


@pytest.mark.verification
def test_poc_swr_009_records_reasoning_governance_metadata(
    engineering_graph: EngineeringGraph,
) -> None:
    timestamp = datetime(2026, 8, 13, tzinfo=UTC)
    failure = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")
    result = DeterministicReasoningFallback().explain_failure(failure, generated_at=timestamp)

    assert result.model_name == "deterministic-evidence-fallback"
    assert result.prompt_version == "rca-v1"
    assert result.generated_at == timestamp
    assert result.confidence == "High"
    assert result.review_decision == "PROPOSED"


@pytest.mark.verification
def test_poc_swr_010_uses_one_application_service_for_complete_report(
    engineering_graph: EngineeringGraph,
) -> None:
    report = EngineeringIntelligenceService(engineering_graph).analyze_requirement("SWE-REQ-014")

    assert report.requirement.artifact_id == "SWE-REQ-014"
    assert report.failure_analysis.first_failure_id == "IT-045"
    assert report.release_eligibility.status == "BLOCKED"


@pytest.mark.verification
def test_poc_swr_011_preserves_original_requirements_analysis(
    sample_data_path: Path, tmp_path: Path
) -> None:
    report, output_paths = run_analysis(
        sample_data_path,
        tmp_path / "outputs",
        generated_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
    )

    assert report.summary.total_requirements == 18
    assert all(path.exists() for path in output_paths)


@pytest.mark.verification
def test_poc_swr_012_ci_contains_required_quality_gates() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    required_commands = (
        "ruff format --check",
        "ruff check",
        "mypy",
        "bandit",
        "pytest --cov",
        "uv build",
        "traceai trace SWE-REQ-014",
        "pip-audit",
    )

    assert all(command in workflow for command in required_commands)
