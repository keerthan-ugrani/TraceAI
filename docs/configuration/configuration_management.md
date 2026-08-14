# Configuration management plan

## Configuration items

Requirements, architecture, interfaces, detailed designs, units, source files, commits,
tests, executions, defects, changes, builds, baselines, and releases are controlled by ID and
version. Relevant artifacts additionally include revision, status, timestamps, baseline, and
approval.

## Baselines

- `REQ-BL-*`: requirements snapshot
- `ARCH-BL-*`: architecture/interface snapshot
- `TEST-BL-*`: verification snapshot
- `BL-*`: integrated product configuration baseline

Builds identify their requirement baseline and product baseline. Releases identify the
approved product baseline and build.

## Deterministic consistency rules

1. Edge `expected_target_version` shall equal the controlled target artifact version.
2. A build requirement baseline shall equal the current requirement baseline when evaluating
   the current implementation.
3. Baseline snapshot versions shall match current versions only when the baseline is marked
   for current comparison.

## Change control

Approved data is read-only in the PoC. AI output is advisory. Changes proceed through Change
Request, commit, build, baseline, verification, and release workflows.
