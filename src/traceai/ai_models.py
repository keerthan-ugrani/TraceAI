"""Validated contracts for TraceAI's governed generative and embedding workflows."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from traceai.engineering_models import ReviewDecision
from traceai.exceptions import TraceAIError


class DataClassification(StrEnum):
    SYNTHETIC = "SYNTHETIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"


class VerificationLevel(StrEnum):
    UNIT = "UNIT"
    COMPONENT = "COMPONENT"
    INTEGRATION = "INTEGRATION"
    SOFTWARE = "SOFTWARE"


class FindingLevel(StrEnum):
    INFO = "INFO"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AIRequirementRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=10)
    source: str
    status: str
    related_artifact_ids: list[str] = Field(default_factory=list)


class AIArtifactDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    artifact_type: str
    name: str
    text: str = Field(min_length=10)
    version: str
    linked_requirement_ids: list[str] = Field(default_factory=list)


class EngineeringLogRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement_id: str
    test_id: str
    component_ids: list[str]
    lines: list[str] = Field(min_length=1)
    expected: str
    actual: str
    evidence_ids: list[str] = Field(min_length=1)


class HistoricalDefectRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    symptoms: list[str]
    root_cause: str
    resolution: str
    component_ids: list[str]
    evidence_ids: list[str] = Field(min_length=1)

    def searchable_text(self) -> str:
        return " ".join(
            [self.title, self.description, *self.symptoms, self.root_cause, self.resolution]
        )


class TestGenerationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    requirement_text: str
    architecture_context: list[str]
    interface_contracts: list[str]
    acceptance_criteria: list[str]
    design_constraints: list[str]
    existing_test_ids: list[str]
    safety_notes: list[str]
    evidence_ids: list[str] = Field(min_length=1)


class AIKnowledgeDataset(BaseModel):
    """Synthetic knowledge used by all six AI enhancements."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    description: str
    data_classification: DataClassification
    requirements: list[AIRequirementRecord]
    candidate_artifacts: list[AIArtifactDocument]
    engineering_logs: list[EngineeringLogRecord]
    historical_defects: list[HistoricalDefectRecord]
    test_generation_contexts: list[TestGenerationContext]

    @model_validator(mode="after")
    def controlled_ids_are_unique(self) -> AIKnowledgeDataset:
        sections = {
            "requirements": [item.id for item in self.requirements],
            "candidate_artifacts": [item.id for item in self.candidate_artifacts],
            "engineering_logs": [item.id for item in self.engineering_logs],
            "historical_defects": [item.id for item in self.historical_defects],
            "test_generation_contexts": [
                item.requirement_id for item in self.test_generation_contexts
            ],
        }
        duplicates = [
            f"{section}:{item_id}"
            for section, ids in sections.items()
            for item_id in sorted({item for item in ids if ids.count(item) > 1})
        ]
        if duplicates:
            raise ValueError("duplicate controlled IDs: " + ", ".join(duplicates))
        return self

    def requirement(self, requirement_id: str) -> AIRequirementRecord:
        for item in self.requirements:
            if item.id == requirement_id:
                return item
        raise TraceAIError(f"Unknown AI knowledge requirement: {requirement_id}")

    def engineering_log(self, log_id: str) -> EngineeringLogRecord:
        for item in self.engineering_logs:
            if item.id == log_id:
                return item
        raise TraceAIError(f"Unknown engineering log: {log_id}")

    def test_context(self, requirement_id: str) -> TestGenerationContext:
        for item in self.test_generation_contexts:
            if item.requirement_id == requirement_id:
                return item
        raise TraceAIError(f"Unknown test-generation requirement: {requirement_id}")


class AIProvenance(BaseModel):
    """Application-owned metadata; the model cannot approve its own output."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model_name: str
    prompt_version: str
    generated_at: datetime
    evidence_ids: list[str]
    live_model_used: bool
    data_classification: DataClassification
    review_decision: ReviewDecision = ReviewDecision.PROPOSED


class RootCauseHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    explanation: str
    confidence: ConfidenceLevel
    evidence_ids: list[str] = Field(min_length=1)


class RootCauseDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    hypotheses: list[RootCauseHypothesis] = Field(min_length=1, max_length=5)
    recommended_checks: list[str] = Field(min_length=1, max_length=8)
    evidence_ids: list[str] = Field(min_length=1)


class RootCauseAIReport(BaseModel):
    requirement_id: str
    first_failure_id: str | None
    analysis: RootCauseDraft
    provenance: AIProvenance


class TraceLinkRecommendation(BaseModel):
    requirement_id: str
    artifact_id: str
    artifact_type: str
    similarity_score: float = Field(ge=0, le=1)
    rationale: str
    evidence_ids: list[str]
    review_decision: ReviewDecision = ReviewDecision.PROPOSED


class TraceLinkReport(BaseModel):
    requirement_id: str
    recommendations: list[TraceLinkRecommendation]
    provenance: AIProvenance


class RequirementQualityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    severity: FindingLevel
    message: str
    suggested_change: str
    evidence_ids: list[str] = Field(min_length=1)


class RequirementQualityDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    rewritten_requirement: str
    findings: list[RequirementQualityFinding]
    verification_notes: list[str]
    evidence_ids: list[str] = Field(min_length=1)


class RequirementQualityReport(BaseModel):
    requirement_id: str
    original_requirement: str
    review: RequirementQualityDraft
    provenance: AIProvenance


class LogAnalysisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    timeline: list[str] = Field(min_length=1)
    anomalies: list[str] = Field(min_length=1)
    hypotheses: list[RootCauseHypothesis] = Field(min_length=1, max_length=5)
    recommended_checks: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class LogAnalysisReport(BaseModel):
    log_id: str
    analysis: LogAnalysisDraft
    provenance: AIProvenance


class SimilarDefectMatch(BaseModel):
    defect_id: str
    title: str
    similarity_score: float = Field(ge=0, le=1)
    similarity_reason: str
    previous_resolution: str
    evidence_ids: list[str]


class SimilarDefectsReport(BaseModel):
    query_id: str
    matches: list[SimilarDefectMatch]
    provenance: AIProvenance


class GeneratedTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str
    title: str
    verification_level: VerificationLevel
    objective: str
    preconditions: list[str]
    steps: list[str] = Field(min_length=1)
    expected_result: str
    test_data: list[str]
    requirement_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    review_decision: ReviewDecision

    @field_validator("test_id")
    @classmethod
    def test_id_is_proposed(cls, value: str) -> str:
        if not value.startswith("AI-TC-"):
            raise ValueError("generated test IDs must start with AI-TC-")
        return value


class TestGenerationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage_summary: str
    test_cases: list[GeneratedTestCase] = Field(min_length=1, max_length=12)
    uncovered_risks: list[str]
    evidence_ids: list[str] = Field(min_length=1)


class TestGenerationReport(BaseModel):
    requirement_id: str
    plan: TestGenerationDraft
    provenance: AIProvenance


class AIEnhancementSuiteReport(BaseModel):
    """One interview artifact containing evidence for all six AI enhancements."""

    root_cause: RootCauseAIReport
    trace_links: TraceLinkReport
    requirement_quality: RequirementQualityReport
    log_analysis: LogAnalysisReport
    similar_defects: SimilarDefectsReport
    test_generation: TestGenerationReport
