"""Deterministic change traversal and stale-artifact detection."""

from __future__ import annotations

from collections import defaultdict

from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import ArtifactType, ChangeImpact
from traceai.traceability import TraceabilityEngine


class ChangeImpactService:
    def __init__(self, graph: EngineeringGraph, traceability: TraceabilityEngine) -> None:
        self.graph = graph
        self.traceability = traceability

    def analyze(self, change_request_id: str) -> ChangeImpact:
        change_request = self.graph.artifact(change_request_id)
        affected = self.traceability.calculate_change_impact(change_request_id)
        grouped: dict[str, list[str]] = defaultdict(list)
        stale: list[str] = []
        ignored_types = {ArtifactType.DEFECT, ArtifactType.CHANGE_REQUEST}
        for artifact in affected:
            if artifact.type not in ignored_types:
                grouped[artifact.type.value].append(artifact.id)
            if artifact.id == change_request_id or artifact.type in ignored_types:
                continue
            if artifact.updated_at < change_request.created_at:
                stale.append(artifact.id)

        grouped_sorted = {key: sorted(values) for key, values in sorted(grouped.items())}
        return ChangeImpact(
            change_request_id=change_request_id,
            affected_by_type=grouped_sorted,
            stale_artifact_ids=sorted(stale),
            summary=(
                f"{sum(len(values) for values in grouped_sorted.values())} artifacts are linked "
                f"to {change_request_id}; {len(stale)} pre-date the change and require review "
                "or re-verification."
            ),
        )
