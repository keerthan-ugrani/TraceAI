# Test strategy

## Levels

- Unit: domain validation and individual deterministic engines
- Integration: JSON → graph → services → evidence → reasoning → report persistence
- Verification: executable acceptance tests mapped to `POC-SWR-*`
- Manual: Streamlit rendering and five-minute demonstration

## Principles

- Test both failing and healthy threads.
- Freeze timestamps in integration output.
- Never call an external LLM in CI.
- Verify categories separately: gap, test failure, configuration mismatch, change risk.
- Maintain branch-aware coverage of at least 85%.
- Bandit `B105` is disabled because controlled status enums use the literal `PASS`; secret
  scanning remains a repository responsibility and all other configured Bandit checks run.

## Commands

```bash
make test-unit
make test-integration
make test-verification
make coverage
```
