# Software architecture

## Components

```mermaid
flowchart TD
    UI["CLI / Streamlit"] --> INTEL["EngineeringIntelligenceService"]
    INTEL --> T["TraceabilityEngine"]
    INTEL --> C["ConfigurationEngine"]
    INTEL --> F["FailureAnalysisService"]
    INTEL --> CH["ChangeImpactService"]
    INTEL --> R["ReleaseEligibilityEngine"]
    T --> G["EngineeringGraph"]
    C --> G
    F --> G
    CH --> G
    R --> G
    G --> A["Validated JSON adapter"]
    F --> E["FailureEvidencePackage"]
    E --> REASON["EngineeringReasoningService"]
    REASON --> RCA["RootCauseAnalysis"]
```

## Dependency rule

Deterministic engines depend on the graph and domain contracts. They never depend on the
reasoning abstraction. The application layer may compose both. UI and CLI depend only on the
application use case, preventing duplicated business rules.

## Persistence boundary

`engineering_loader.py` is the current adapter. A production adapter may retrieve artifacts
from ALM, Git, test management, defect management, configuration, and release systems and
then populate the same `EngineeringDataset` contract.

## Scale path

For the four-day PoC, indexed in-memory traversal is simpler and more reliable than a graph
database. At enterprise scale, implement an audited relational/graph repository adapter,
pagination, incremental synchronization, access control, and immutable event history.
