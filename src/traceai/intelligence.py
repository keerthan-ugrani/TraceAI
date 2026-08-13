"""Application service composing deterministic engines and advisory reasoning."""

from __future__ import annotations

from datetime import UTC, datetime

from traceai.change_impact import ChangeImpactService
from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import (
    ArtifactStatus,
    ArtifactType,
    EngineeringIntelligenceReport,
    OverallHealth,
    TraceStep,
)
from traceai.failure_analysis import FailureAnalysisService
from traceai.reasoning import DeterministicReasoningFallback, EngineeringReasoningService
from traceai.release import ReleaseEligibilityEngine
from traceai.traceability import TraceabilityEngine


class EngineeringIntelligenceService:
    """Stable use case used by CLI, integration tests, and Streamlit."""

    def __init__(
        self,
        graph: EngineeringGraph,
        reasoning: EngineeringReasoningService | None = None,
    ) -> None:
        self.graph = graph
        self.traceability = TraceabilityEngine(graph)
        self.configuration = ConfigurationEngine(graph)
        self.failures = FailureAnalysisService(graph, self.configuration)
        self.changes = ChangeImpactService(graph, self.traceability)
        self.releases = ReleaseEligibilityEngine(graph, self.traceability, self.configuration)
        self.reasoning = reasoning or DeterministicReasoningFallback()

    def analyze_requirement(
        self,
        requirement_id: str,
        *,
        release_id: str | None = None,
        change_request_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> EngineeringIntelligenceReport:
        timestamp = generated_at or datetime.now(UTC)
        requirement = self.graph.artifact(requirement_id)
        digital_thread = self.traceability.get_full_trace(requirement_id)
        gaps = self.traceability.find_missing_links(requirement_id)
        mismatches = self.configuration.find_mismatches(requirement_id)
        failure = self.failures.analyze(requirement_id)

        hero_requirement_id = str(self.graph.dataset.metadata.get("hero_requirement_id", ""))
        hero_release_id = str(self.graph.dataset.metadata.get("hero_release_id", ""))
        resolved_release_id = release_id or (
            hero_release_id if requirement_id == hero_requirement_id else ""
        )
        if not resolved_release_id:
            releases = [
                step for step in digital_thread if step.artifact_type is ArtifactType.RELEASE
            ]
            resolved_release_id = releases[0].artifact_id

        resolved_change_id = change_request_id or self._first_connected_id(
            requirement_id, ArtifactType.CHANGE_REQUEST
        )
        change_impact = self.changes.analyze(resolved_change_id) if resolved_change_id else None
        release_eligibility = self.releases.evaluate(requirement_id, resolved_release_id)
        rca = self.reasoning.explain_failure(failure, generated_at=timestamp)
        open_defects = [
            artifact.id
            for artifact in self.graph.connected_by_type(requirement_id, {ArtifactType.DEFECT})
            if artifact.status is ArtifactStatus.OPEN
        ]
        overall = (
            OverallHealth.BLOCKED
            if release_eligibility.blocking_reasons
            else OverallHealth.AT_RISK
            if gaps or mismatches
            else OverallHealth.HEALTHY
        )
        return EngineeringIntelligenceReport(
            generated_at=timestamp,
            requirement=TraceStep(
                artifact_id=requirement.id,
                artifact_type=requirement.type,
                name=requirement.name,
                version=requirement.version,
                status=requirement.status,
                baseline_id=requirement.baseline_id,
            ),
            overall_health=overall,
            metrics=self.traceability.calculate_traceability_coverage(requirement_id),
            digital_thread=digital_thread,
            missing_links=gaps,
            configuration_mismatches=mismatches,
            failure_analysis=failure,
            root_cause_analysis=rca,
            change_impact=change_impact,
            release_eligibility=release_eligibility,
            open_defect_ids=sorted(open_defects),
            known_limitations=[
                "Synthetic standalone data; no live ALM, PLM, Git, or CI integration.",
                "Root-cause output is advisory and requires accountable engineering review.",
                "PoC process mapping does not constitute Automotive SPICE assessment or "
                "certification.",
            ],
        )

    def _first_connected_id(self, artifact_id: str, artifact_type: ArtifactType) -> str | None:
        artifacts = self.graph.connected_by_type(artifact_id, {artifact_type})
        return artifacts[0].id if artifacts else None
