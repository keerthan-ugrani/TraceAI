"""Focused tests for evidence-grounded advisory reasoning."""

from datetime import UTC, datetime

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.failure_analysis import FailureAnalysisService
from traceai.reasoning import DeterministicReasoningFallback


def test_reasoning_is_grounded_and_auditable(engineering_graph: EngineeringGraph) -> None:
    failure = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")

    result = DeterministicReasoningFallback().explain_failure(
        failure, generated_at=datetime(2026, 8, 13, tzinfo=UTC)
    )

    assert "probable" in result.probable_root_cause.lower()
    assert result.confidence == "High"
    assert {"IT-045", "ARCH-IF-006"} <= set(result.evidence_ids)
    assert result.review_decision == "PROPOSED"


def test_reasoning_records_model_prompt_and_generation_time(
    engineering_graph: EngineeringGraph,
) -> None:
    failure = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")
    generated_at = datetime(2026, 8, 13, tzinfo=UTC)

    result = DeterministicReasoningFallback().explain_failure(failure, generated_at=generated_at)

    assert result.model_name == "deterministic-evidence-fallback"
    assert result.prompt_version == "rca-v1"
    assert result.generated_at == generated_at


def test_healthy_thread_does_not_invent_a_root_cause(
    engineering_graph: EngineeringGraph,
) -> None:
    failure = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-030")

    result = DeterministicReasoningFallback().explain_failure(failure)

    assert result.confidence == "Low"
    assert "no failed verification" in result.probable_root_cause
    assert failure.first_failure_id is None
    assert result.suspected_component_ids == []
    assert result.suspected_interface_ids == []
