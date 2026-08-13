"""Dependency-free, bidirectional traversal over validated engineering artifacts."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from traceai.engineering_models import (
    Artifact,
    ArtifactType,
    EngineeringDataset,
    Relationship,
    RelationshipType,
)
from traceai.exceptions import ArtifactNotFoundError

STAGE_ORDER: dict[ArtifactType, int] = {
    ArtifactType.SYSTEM_REQUIREMENT: 10,
    ArtifactType.SOFTWARE_REQUIREMENT: 20,
    ArtifactType.ARCHITECTURE_COMPONENT: 30,
    ArtifactType.ARCHITECTURE_INTERFACE: 35,
    ArtifactType.DETAILED_DESIGN: 40,
    ArtifactType.SOFTWARE_UNIT: 50,
    ArtifactType.SOURCE_FILE: 60,
    ArtifactType.COMMIT: 70,
    ArtifactType.UNIT_TEST: 80,
    ArtifactType.COMPONENT_TEST: 90,
    ArtifactType.INTEGRATION_TEST: 100,
    ArtifactType.SOFTWARE_VERIFICATION_TEST: 110,
    ArtifactType.TEST_EXECUTION: 115,
    ArtifactType.DEFECT: 120,
    ArtifactType.CHANGE_REQUEST: 125,
    ArtifactType.BUILD: 130,
    ArtifactType.BASELINE: 140,
    ArtifactType.RELEASE: 150,
}


class EngineeringGraph:
    """Index graph data once and expose deterministic traversal operations."""

    def __init__(self, dataset: EngineeringDataset) -> None:
        self.dataset = dataset
        self._artifacts = {artifact.id: artifact for artifact in dataset.artifacts}
        self._outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self._incoming: dict[str, list[Relationship]] = defaultdict(list)
        for relationship in dataset.relationships:
            self._outgoing[relationship.source_id].append(relationship)
            self._incoming[relationship.target_id].append(relationship)

    def artifact(self, artifact_id: str) -> Artifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(f"Unknown engineering artifact: {artifact_id}") from exc

    def artifacts(self, artifact_ids: Iterable[str]) -> list[Artifact]:
        return [self.artifact(artifact_id) for artifact_id in artifact_ids]

    def relationships_for(self, artifact_id: str) -> list[Relationship]:
        self.artifact(artifact_id)
        relationships = [*self._outgoing[artifact_id], *self._incoming[artifact_id]]
        return sorted(relationships, key=lambda relationship: relationship.id)

    def neighbors(
        self,
        artifact_id: str,
        *,
        relationship_types: set[RelationshipType] | None = None,
        direction: str = "both",
    ) -> list[Artifact]:
        self.artifact(artifact_id)
        relationships: list[Relationship] = []
        if direction in {"out", "both"}:
            relationships.extend(self._outgoing[artifact_id])
        if direction in {"in", "both"}:
            relationships.extend(self._incoming[artifact_id])
        if direction not in {"out", "in", "both"}:
            raise ValueError("direction must be 'out', 'in', or 'both'")

        ids: set[str] = set()
        for relationship in relationships:
            if relationship_types and relationship.type not in relationship_types:
                continue
            other_id = (
                relationship.target_id
                if relationship.source_id == artifact_id
                else relationship.source_id
            )
            ids.add(other_id)
        return self.sorted_artifacts(ids)

    def connected_ids(self, start_id: str, *, max_depth: int = 20) -> set[str]:
        """Return the complete local digital thread, following every edge in either direction."""
        self.artifact(start_id)
        visited = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        while queue:
            artifact_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor in self.neighbors(artifact_id):
                if neighbor.id in visited:
                    continue
                visited.add(neighbor.id)
                queue.append((neighbor.id, depth + 1))
        return visited

    def connected_by_type(
        self, start_id: str, artifact_types: set[ArtifactType], *, max_depth: int = 20
    ) -> list[Artifact]:
        return [
            artifact
            for artifact in self.sorted_artifacts(self.connected_ids(start_id, max_depth=max_depth))
            if artifact.type in artifact_types
        ]

    def has_neighbor(
        self,
        artifact_id: str,
        *,
        artifact_types: set[ArtifactType],
        relationship_types: set[RelationshipType] | None = None,
    ) -> bool:
        return any(
            neighbor.type in artifact_types
            for neighbor in self.neighbors(
                artifact_id,
                relationship_types=relationship_types,
            )
        )

    def find_relationships(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        relationship_type: RelationshipType | None = None,
    ) -> list[Relationship]:
        relationships = self.dataset.relationships
        if source_id is not None:
            relationships = [item for item in relationships if item.source_id == source_id]
        if target_id is not None:
            relationships = [item for item in relationships if item.target_id == target_id]
        if relationship_type is not None:
            relationships = [item for item in relationships if item.type is relationship_type]
        return sorted(relationships, key=lambda relationship: relationship.id)

    def sorted_artifacts(self, artifact_ids: Iterable[str]) -> list[Artifact]:
        return sorted(
            (self.artifact(artifact_id) for artifact_id in set(artifact_ids)),
            key=lambda artifact: (STAGE_ORDER[artifact.type], artifact.id),
        )
