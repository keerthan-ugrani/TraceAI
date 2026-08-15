# Detailed design

## Engineering graph

- Dictionary lookup provides artifact resolution.
- Incoming and outgoing adjacency indexes enable bidirectional navigation.
- Breadth-first search reconstructs the connected thread.
- Stage-order metadata produces deterministic V-model presentation.

## Traceability engine

The engine filters connected artifacts into the core thread and runs type-specific mandatory
link rules. Findings use a separate `TRACEABILITY_GAP` category.

## Configuration engine

The engine compares edge-level version expectations, current requirement baseline versus
build baseline, and explicitly selected baseline snapshots. It performs exact string
comparison for the PoC.

## Failure analysis

Failed mandatory tests are ordered by verification level. The calculated propagation view is
not written back to the dataset. Evidence collection returns a Pydantic model before advisory
reasoning begins.

## Reasoning

`EngineeringReasoningService` is a protocol. The offline fallback is deterministic and
ensures reproducible demonstration/CI. A future LLM adapter must accept the same evidence
model and return a valid `RootCauseAnalysis`.

## Release eligibility

Release eligibility is a pure deterministic decision. Reasons and evidence IDs remain visible
to the UI and report.
