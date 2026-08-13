"""Validated contracts for the ASPICE-oriented engineering digital thread."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ArtifactType(StrEnum):
    SYSTEM_REQUIREMENT = "SYSTEM_REQUIREMENT"
    SOFTWARE_REQUIREMENT = "SOFTWARE_REQUIREMENT"
    ARCHITECTURE_COMPONENT = "ARCHITECTURE_COMPONENT"
    ARCHITECTURE_INTERFACE = "ARCHITECTURE_INTERFACE"
    DETAILED_DESIGN = "DETAILED_DESIGN"
    SOFTWARE_UNIT = "SOFTWARE_UNIT"
    SOURCE_FILE = "SOURCE_FILE"
    COMMIT = "COMMIT"
    UNIT_TEST = "UNIT_TEST"
    COMPONENT_TEST = "COMPONENT_TEST"
    INTEGRATION_TEST = "INTEGRATION_TEST"
    SOFTWARE_VERIFICATION_TEST = "SOFTWARE_VERIFICATION_TEST"
    TEST_EXECUTION = "TEST_EXECUTION"
    DEFECT = "DEFECT"
    CHANGE_REQUEST = "CHANGE_REQUEST"
    BUILD = "BUILD"
    BASELINE = "BASELINE"
    RELEASE = "RELEASE"


class ArtifactStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    WARNING = "WARNING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PROPOSED = "PROPOSED"
    CANDIDATE = "CANDIDATE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    RELEASED = "RELEASED"


class RelationshipType(StrEnum):
    DERIVED_FROM = "DERIVED_FROM"
    ALLOCATED_TO = "ALLOCATED_TO"
    DESIGNED_BY = "DESIGNED_BY"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    MODIFIED_BY = "MODIFIED_BY"
    VERIFIED_BY = "VERIFIED_BY"
    EXECUTED_AS = "EXECUTED_AS"
    DEPENDS_ON = "DEPENDS_ON"
    INTERFACES_WITH = "INTERFACES_WITH"
    RAISED_DEFECT = "RAISED_DEFECT"
    RESOLVED_BY = "RESOLVED_BY"
    CHANGED_BY = "CHANGED_BY"
    INCLUDED_IN_BUILD = "INCLUDED_IN_BUILD"
    INCLUDED_IN_BASELINE = "INCLUDED_IN_BASELINE"
    RELEASED_IN = "RELEASED_IN"


class FindingSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class EngineeringIssueCategory(StrEnum):
    TRACEABILITY_GAP = "TRACEABILITY_GAP"
    TEST_FAILURE = "TEST_FAILURE"
    CONFIGURATION_MISMATCH = "CONFIGURATION_MISMATCH"
    CHANGE_IMPACT_RISK = "CHANGE_IMPACT_RISK"


class OverallHealth(StrEnum):
    HEALTHY = "HEALTHY"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"


class ReleaseStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


class ReviewDecision(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class Artifact(BaseModel):
    """One versioned, configuration-controlled engineering artifact."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=3, max_length=120)
    type: ArtifactType
    name: str = Field(min_length=2, max_length=200)
    version: str = Field(min_length=1, max_length=40)
    status: ArtifactStatus
    revision: int = Field(default=1, ge=1)
    baseline_id: str | None = None
    created_at: datetime
    updated_at: datetime
    approved_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_artifact_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,119}", value):
            raise ValueError("artifact id contains unsupported characters")
        return value

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> Artifact:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self


class Relationship(BaseModel):
    """A typed, auditable edge between two engineering artifacts."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_id: str
    target_id: str
    type: RelationshipType
    status: ArtifactStatus = ArtifactStatus.APPROVED
    created_at: datetime
    source: str = "synthetic-demo-data"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngineeringDataset(BaseModel):
    """Portable persistence contract used by the local JSON adapter."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    description: str
    artifacts: list[Artifact]
    relationships: list[Relationship]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_graph_references(self) -> EngineeringDataset:
        artifact_ids = [artifact.id for artifact in self.artifacts]
        duplicate_artifacts = _duplicates(artifact_ids)
        relationship_ids = [relationship.id for relationship in self.relationships]
        duplicate_relationships = _duplicates(relationship_ids)
        if duplicate_artifacts:
            raise ValueError(f"duplicate artifact IDs: {', '.join(duplicate_artifacts)}")
        if duplicate_relationships:
            raise ValueError(f"duplicate relationship IDs: {', '.join(duplicate_relationships)}")

        known_ids = set(artifact_ids)
        dangling = [
            relationship.id
            for relationship in self.relationships
            if relationship.source_id not in known_ids or relationship.target_id not in known_ids
        ]
        if dangling:
            raise ValueError(f"relationships reference unknown artifacts: {', '.join(dangling)}")
        return self


class TraceStep(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    name: str
    version: str
    status: ArtifactStatus
    baseline_id: str | None = None


class TraceabilityGap(BaseModel):
    category: EngineeringIssueCategory = EngineeringIssueCategory.TRACEABILITY_GAP
    severity: FindingSeverity
    artifact_id: str
    message: str
    expected_artifact_type: ArtifactType | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ConfigurationMismatch(BaseModel):
    category: EngineeringIssueCategory = EngineeringIssueCategory.CONFIGURATION_MISMATCH
    artifact_id: str
    context: str
    expected_version: str
    actual_version: str
    evidence_ids: list[str]


class TraceabilityMetrics(BaseModel):
    overall_coverage_percent: float = Field(ge=0, le=100)
    verification_percent: float = Field(ge=0, le=100)
    stage_coverage_percent: dict[str, float]
    missing_link_count: int = Field(ge=0)


class FailureEvidencePackage(BaseModel):
    requirement_id: str
    architecture_ids: list[str]
    software_unit_ids: list[str]
    tests_by_status: dict[str, list[str]]
    failed_test_id: str | None
    failure_level: str | None
    expected_value: str | None
    actual_value: str | None
    failure_message: str | None
    runtime_log: str | None
    interface_ids: list[str]
    commit_ids: list[str]
    changed_files: list[str]
    previous_test_runs: list[str]
    configuration_mismatch_ids: list[str]
    defect_ids: list[str]
    change_request_ids: list[str]
    build_ids: list[str]
    baseline_ids: list[str]
    release_ids: list[str]


class Suspect(BaseModel):
    artifact_id: str
    probability_percent: float = Field(ge=0, le=100)
    reason: str
    evidence_ids: list[str]


class FailureAnalysis(BaseModel):
    category: EngineeringIssueCategory | None = None
    first_failure_id: str | None
    failure_level: str | None
    localization_summary: str
    propagated_statuses: dict[str, str]
    suspects: list[Suspect]
    evidence: FailureEvidencePackage


class RootCauseAnalysis(BaseModel):
    title: str
    probable_root_cause: str
    confidence: str
    suspected_component_ids: list[str]
    suspected_interface_ids: list[str]
    observations: list[str]
    evidence_ids: list[str]
    recommended_checks: list[str]
    model_name: str
    prompt_version: str
    generated_at: datetime
    review_decision: ReviewDecision = ReviewDecision.PROPOSED


class ChangeImpact(BaseModel):
    category: EngineeringIssueCategory = EngineeringIssueCategory.CHANGE_IMPACT_RISK
    change_request_id: str
    affected_by_type: dict[str, list[str]]
    stale_artifact_ids: list[str]
    summary: str


class ReleaseEligibility(BaseModel):
    release_id: str
    status: ReleaseStatus
    blocking_reasons: list[str]
    evidence_ids: list[str]


class EngineeringIntelligenceReport(BaseModel):
    generated_at: datetime
    requirement: TraceStep
    overall_health: OverallHealth
    metrics: TraceabilityMetrics
    digital_thread: list[TraceStep]
    missing_links: list[TraceabilityGap]
    configuration_mismatches: list[ConfigurationMismatch]
    failure_analysis: FailureAnalysis
    root_cause_analysis: RootCauseAnalysis
    change_impact: ChangeImpact | None
    release_eligibility: ReleaseEligibility
    open_defect_ids: list[str]
    known_limitations: list[str]


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)
