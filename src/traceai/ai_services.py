"""Governed application services implementing AI Enhancements 1 through 6."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from traceai.ai_gateway import AIModelGateway, cosine_similarity
from traceai.ai_models import (
    AIKnowledgeDataset,
    AIProvenance,
    DataClassification,
    LogAnalysisDraft,
    LogAnalysisReport,
    RequirementQualityDraft,
    RequirementQualityReport,
    RootCauseAIReport,
    RootCauseDraft,
    SimilarDefectMatch,
    SimilarDefectsReport,
    TestGenerationDraft,
    TestGenerationReport,
    TraceLinkRecommendation,
    TraceLinkReport,
)
from traceai.ai_prompts import (
    LOG_ANALYSIS_PROMPT_VERSION,
    LOG_ANALYSIS_SYSTEM_PROMPT,
    RCA_PROMPT_VERSION,
    RCA_SYSTEM_PROMPT,
    REQUIREMENT_REVIEW_PROMPT_VERSION,
    REQUIREMENT_REVIEW_SYSTEM_PROMPT,
    SIMILAR_DEFECT_PROMPT_VERSION,
    TEST_GENERATION_PROMPT_VERSION,
    TEST_GENERATION_SYSTEM_PROMPT,
    TRACE_LINK_PROMPT_VERSION,
)
from traceai.configuration import ConfigurationEngine
from traceai.engineering_graph import EngineeringGraph
from traceai.engineering_models import ReviewDecision
from traceai.exceptions import AIGovernanceError, TraceAIError
from traceai.failure_analysis import FailureAnalysisService


class AIEngineeringCopilot:
    """Compose real model calls with deterministic retrieval and governance checks."""

    def __init__(
        self,
        knowledge: AIKnowledgeDataset,
        graph: EngineeringGraph,
        gateway: AIModelGateway,
    ) -> None:
        if (
            gateway.live_model_used
            and knowledge.data_classification is not DataClassification.SYNTHETIC
        ):
            raise AIGovernanceError(
                "Live model calls are allowed only for the synthetic PoC dataset."
            )
        self.knowledge = knowledge
        self.graph = graph
        self.gateway = gateway

    def analyze_root_cause(
        self, requirement_id: str, *, generated_at: datetime | None = None
    ) -> RootCauseAIReport:
        """Enhancement 1: real, evidence-grounded structured LLM root-cause hypotheses."""
        failure = FailureAnalysisService(self.graph, ConfigurationEngine(self.graph)).analyze(
            requirement_id
        )
        allowed = _failure_evidence_ids(requirement_id, failure.model_dump(mode="json"))
        draft = self.gateway.generate_structured(
            RootCauseDraft,
            system_prompt=RCA_SYSTEM_PROMPT,
            user_payload={
                "task": "Generate evidence-grounded root-cause hypotheses.",
                "requirement_id": requirement_id,
                "failure_analysis": failure.model_dump(mode="json"),
                "allowed_evidence_ids": sorted(allowed),
            },
        )
        cited = _validate_citations(draft, allowed)
        return RootCauseAIReport(
            requirement_id=requirement_id,
            first_failure_id=failure.first_failure_id,
            analysis=draft,
            provenance=self._provenance(RCA_PROMPT_VERSION, cited, generated_at),
        )

    def recommend_trace_links(
        self,
        requirement_id: str,
        *,
        top_k: int = 3,
        minimum_score: float = 0.0,
        generated_at: datetime | None = None,
    ) -> TraceLinkReport:
        """Enhancement 2: embedding-ranked candidate trace links for human approval."""
        if top_k < 1:
            raise TraceAIError("top_k must be at least 1")
        requirement = self.knowledge.requirement(requirement_id)
        candidates = [
            item
            for item in self.knowledge.candidate_artifacts
            if item.id not in requirement.related_artifact_ids
        ]
        texts = [requirement.text] + [
            f"{item.name}. {item.text}. Type {item.artifact_type}." for item in candidates
        ]
        vectors = self.gateway.embed(texts)
        if len(vectors) != len(texts):
            raise AIGovernanceError("Embedding provider returned the wrong vector count")
        scored = sorted(
            (
                (cosine_similarity(vectors[0], vector), candidate)
                for candidate, vector in zip(candidates, vectors[1:], strict=True)
            ),
            key=lambda item: (-item[0], item[1].id),
        )
        recommendations = [
            TraceLinkRecommendation(
                requirement_id=requirement_id,
                artifact_id=candidate.id,
                artifact_type=candidate.artifact_type,
                similarity_score=round(max(0.0, min(1.0, score)), 4),
                rationale=(
                    "Embedding similarity indicates related engineering terminology; an "
                    "engineer must inspect semantics and configuration before accepting it."
                ),
                evidence_ids=[requirement_id, candidate.id],
            )
            for score, candidate in scored
            if score >= minimum_score
        ][:top_k]
        evidence_ids = sorted(
            {item for recommendation in recommendations for item in recommendation.evidence_ids}
        )
        return TraceLinkReport(
            requirement_id=requirement_id,
            recommendations=recommendations,
            provenance=self._provenance(TRACE_LINK_PROMPT_VERSION, evidence_ids, generated_at),
        )

    def review_requirement(
        self, requirement_id: str, *, generated_at: datetime | None = None
    ) -> RequirementQualityReport:
        """Enhancement 3: semantic quality review and measurable rewrite proposal."""
        requirement = self.knowledge.requirement(requirement_id)
        allowed = {requirement.id, *requirement.related_artifact_ids}
        draft = self.gateway.generate_structured(
            RequirementQualityDraft,
            system_prompt=REQUIREMENT_REVIEW_SYSTEM_PROMPT,
            user_payload={
                "task": "Review requirement quality and propose a measurable rewrite.",
                "requirement_id": requirement.id,
                "requirement_text": requirement.text,
                "source": requirement.source,
                "status": requirement.status,
                "allowed_evidence_ids": sorted(allowed),
            },
        )
        cited = _validate_citations(draft, allowed)
        return RequirementQualityReport(
            requirement_id=requirement.id,
            original_requirement=requirement.text,
            review=draft,
            provenance=self._provenance(REQUIREMENT_REVIEW_PROMPT_VERSION, cited, generated_at),
        )

    def analyze_log(
        self, log_id: str, *, generated_at: datetime | None = None
    ) -> LogAnalysisReport:
        """Enhancement 4: structured log chronology, anomaly, and hypothesis analysis."""
        log = self.knowledge.engineering_log(log_id)
        allowed = {
            log.id,
            log.requirement_id,
            log.test_id,
            *log.component_ids,
            *log.evidence_ids,
        }
        draft = self.gateway.generate_structured(
            LogAnalysisDraft,
            system_prompt=LOG_ANALYSIS_SYSTEM_PROMPT,
            user_payload={
                "task": "Analyze the engineering log without inventing events.",
                "log_id": log.id,
                "requirement_id": log.requirement_id,
                "test_id": log.test_id,
                "component_ids": log.component_ids,
                "expected": log.expected,
                "actual": log.actual,
                "lines": log.lines,
                "allowed_evidence_ids": sorted(allowed),
            },
        )
        cited = _validate_citations(draft, allowed)
        return LogAnalysisReport(
            log_id=log.id,
            analysis=draft,
            provenance=self._provenance(LOG_ANALYSIS_PROMPT_VERSION, cited, generated_at),
        )

    def retrieve_similar_defects(
        self,
        log_id: str,
        *,
        top_k: int = 3,
        generated_at: datetime | None = None,
    ) -> SimilarDefectsReport:
        """Enhancement 5: embedding retrieval over controlled historical defect records."""
        if top_k < 1:
            raise TraceAIError("top_k must be at least 1")
        log = self.knowledge.engineering_log(log_id)
        query = " ".join(
            [
                log.expected,
                log.actual,
                *log.component_ids,
                *log.lines,
            ]
        )
        texts = [query] + [item.searchable_text() for item in self.knowledge.historical_defects]
        vectors = self.gateway.embed(texts)
        if len(vectors) != len(texts):
            raise AIGovernanceError("Embedding provider returned the wrong vector count")
        scored = sorted(
            (
                (cosine_similarity(vectors[0], vector), defect)
                for defect, vector in zip(
                    self.knowledge.historical_defects, vectors[1:], strict=True
                )
            ),
            key=lambda item: (-item[0], item[1].id),
        )[:top_k]
        matches = [
            SimilarDefectMatch(
                defect_id=defect.id,
                title=defect.title,
                similarity_score=round(max(0.0, min(1.0, score)), 4),
                similarity_reason=(
                    "Embedding similarity links the current log symptoms to the controlled "
                    "historical defect text; it does not prove an identical root cause."
                ),
                previous_resolution=defect.resolution,
                evidence_ids=sorted({log.id, defect.id, *defect.evidence_ids}),
            )
            for score, defect in scored
        ]
        evidence_ids = sorted({item for match in matches for item in match.evidence_ids})
        return SimilarDefectsReport(
            query_id=log.id,
            matches=matches,
            provenance=self._provenance(SIMILAR_DEFECT_PROMPT_VERSION, evidence_ids, generated_at),
        )

    def generate_tests(
        self, requirement_id: str, *, generated_at: datetime | None = None
    ) -> TestGenerationReport:
        """Enhancement 6: structured proposed tests with trace evidence and review state."""
        context = self.knowledge.test_context(requirement_id)
        allowed = {context.requirement_id, *context.evidence_ids, *context.existing_test_ids}
        draft = self.gateway.generate_structured(
            TestGenerationDraft,
            system_prompt=TEST_GENERATION_SYSTEM_PROMPT,
            user_payload={
                "task": "Generate proposed verification cases without claiming execution.",
                **context.model_dump(mode="json"),
                "allowed_evidence_ids": sorted(allowed),
            },
        )
        cited = _validate_citations(draft, allowed)
        _validate_generated_tests(draft, context.requirement_id)
        return TestGenerationReport(
            requirement_id=context.requirement_id,
            plan=draft,
            provenance=self._provenance(TEST_GENERATION_PROMPT_VERSION, cited, generated_at),
        )

    def _provenance(
        self, prompt_version: str, evidence_ids: list[str], generated_at: datetime | None
    ) -> AIProvenance:
        return AIProvenance(
            provider=self.gateway.provider_name,
            model_name=(
                self.gateway.embedding_model
                if prompt_version in {TRACE_LINK_PROMPT_VERSION, SIMILAR_DEFECT_PROMPT_VERSION}
                else self.gateway.generation_model
            ),
            prompt_version=prompt_version,
            generated_at=generated_at or datetime.now(UTC),
            evidence_ids=sorted(set(evidence_ids)),
            live_model_used=self.gateway.live_model_used,
            data_classification=self.knowledge.data_classification,
        )


def _failure_evidence_ids(requirement_id: str, payload: dict[str, Any]) -> set[str]:
    evidence_ids = {requirement_id}

    def collect(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, child_key)
        elif isinstance(value, list):
            for child in value:
                collect(child, key)
        elif isinstance(value, str) and (
            key == "artifact_id"
            or key == "first_failure_id"
            or key == "requirement_id"
            or (key is not None and (key.endswith("_id") or key.endswith("_ids")))
        ):
            evidence_ids.add(value)

    collect(payload)
    return evidence_ids


def _validate_citations(model: BaseModel, allowed: set[str]) -> list[str]:
    cited: set[str] = set()

    def collect(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, child_key)
        elif isinstance(value, list):
            for child in value:
                collect(child, key)
        elif key == "evidence_ids" and isinstance(value, str):
            cited.add(value)

    collect(model.model_dump(mode="json"))
    unknown = sorted(cited - allowed)
    if unknown:
        raise AIGovernanceError("Model cited unknown evidence IDs: " + ", ".join(unknown))
    if not cited:
        raise AIGovernanceError("Model output did not cite controlled evidence")
    return sorted(cited)


def _validate_generated_tests(draft: TestGenerationDraft, requirement_id: str) -> None:
    ids = [test.test_id for test in draft.test_cases]
    if len(ids) != len(set(ids)):
        raise AIGovernanceError("Model generated duplicate test IDs")
    for test in draft.test_cases:
        if test.review_decision is not ReviewDecision.PROPOSED:
            raise AIGovernanceError("Generated tests must remain PROPOSED")
        if requirement_id not in test.requirement_ids:
            raise AIGovernanceError(
                f"Generated test {test.test_id} does not trace to {requirement_id}"
            )
