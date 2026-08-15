"""Unit tests for first-failure localization and propagation."""

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.failure_analysis import FailureAnalysisService


def test_localizes_first_failure_to_integration(engineering_graph: EngineeringGraph) -> None:
    service = FailureAnalysisService(engineering_graph, ConfigurationEngine(engineering_graph))

    result = service.analyze("SWE-REQ-014")

    assert result.first_failure_id == "IT-045"
    assert result.failure_level == "Integration Verification (SWE.5)"
    assert "component interaction" in result.localization_summary


def test_propagates_failure_only_to_affected_candidate(
    engineering_graph: EngineeringGraph,
) -> None:
    result = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-014")

    assert result.propagated_statuses["SWE6-VT-008"] == "BLOCKED"
    assert result.propagated_statuses["BUILD-158"] == "NOT_RELEASE_ELIGIBLE"
    assert result.propagated_statuses["REL-1.4.0"] == "AT_RISK"
    assert "BUILD-162" not in result.propagated_statuses
    assert "REL-1.4.1" not in result.propagated_statuses


def test_evidence_contains_failure_values_history_and_changes(
    engineering_graph: EngineeringGraph,
) -> None:
    evidence = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).collect_failure_evidence("SWE-REQ-014")

    assert evidence.expected_value == "ALIGNED"
    assert evidence.actual_value == "VALID"
    assert evidence.previous_test_runs == ["IT-045-RUN-001", "IT-045-RUN-002"]
    assert "CR-091" in evidence.change_request_ids
    assert "DEFECT-023" in evidence.defect_ids


def test_healthy_thread_has_no_first_failure(engineering_graph: EngineeringGraph) -> None:
    result = FailureAnalysisService(
        engineering_graph, ConfigurationEngine(engineering_graph)
    ).analyze("SWE-REQ-030")

    assert result.first_failure_id is None
    assert result.propagated_statuses == {}
