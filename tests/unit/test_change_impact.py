"""Focused tests for deterministic change-impact analysis."""

from traceai.change_impact import ChangeImpactService
from traceai.engineering_graph import EngineeringGraph
from traceai.traceability import TraceabilityEngine


def test_change_impact_groups_connected_artifacts(
    engineering_graph: EngineeringGraph,
) -> None:
    impact = ChangeImpactService(engineering_graph, TraceabilityEngine(engineering_graph)).analyze(
        "CR-091"
    )

    assert "SW-UNIT-007" in impact.affected_by_type["SOFTWARE_UNIT"]
    assert "IT-045" in impact.affected_by_type["INTEGRATION_TEST"]
    assert "REL-1.4.0" in impact.affected_by_type["RELEASE"]
    assert "CHANGE_REQUEST" not in impact.affected_by_type
    assert "DEFECT" not in impact.affected_by_type


def test_change_impact_marks_pre_change_artifacts_for_review(
    engineering_graph: EngineeringGraph,
) -> None:
    impact = ChangeImpactService(engineering_graph, TraceabilityEngine(engineering_graph)).analyze(
        "CR-091"
    )

    assert "SW-UNIT-008" in impact.stale_artifact_ids
    assert "IT-045" in impact.stale_artifact_ids
    assert "33 artifacts" in impact.summary
    assert "26 pre-date the change" in impact.summary
