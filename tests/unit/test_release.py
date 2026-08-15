"""Focused tests for deterministic release eligibility."""

from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.release import ReleaseEligibilityEngine
from traceai.traceability import TraceabilityEngine


def _release_engine(graph: EngineeringGraph) -> ReleaseEligibilityEngine:
    return ReleaseEligibilityEngine(
        graph,
        TraceabilityEngine(graph),
        ConfigurationEngine(graph),
    )


def test_release_is_blocked_by_independent_engineering_evidence(
    engineering_graph: EngineeringGraph,
) -> None:
    result = _release_engine(engineering_graph).evaluate("SWE-REQ-014", "REL-1.4.0")

    assert result.status == "BLOCKED"
    assert any("critical traceability" in reason for reason in result.blocking_reasons)
    assert any("Mandatory verification" in reason for reason in result.blocking_reasons)
    assert any("Blocking defects" in reason for reason in result.blocking_reasons)
    assert any("configuration mismatch" in reason for reason in result.blocking_reasons)


def test_blocked_release_returns_auditable_evidence_ids(
    engineering_graph: EngineeringGraph,
) -> None:
    result = _release_engine(engineering_graph).evaluate("SWE-REQ-014", "REL-1.4.0")

    assert {"REL-1.4.0", "IT-045", "DEFECT-023", "BUILD-158"} <= set(result.evidence_ids)


def test_healthy_release_is_eligible(engineering_graph: EngineeringGraph) -> None:
    result = _release_engine(engineering_graph).evaluate("SWE-REQ-030", "REL-1.5.0")

    assert result.status == "ELIGIBLE"
    assert result.blocking_reasons == []
    assert result.evidence_ids == ["REL-1.5.0"]
