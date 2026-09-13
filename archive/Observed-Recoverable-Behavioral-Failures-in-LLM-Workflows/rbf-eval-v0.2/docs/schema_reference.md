# Schema Reference

Required fields:

- `id`: stable item identifier
- `mode`: taxonomy code such as `PTS`, `QI`, or `EBC`
- `task_family`: broad class such as `retrieval_retry`, `quantitative_consistency`, or `artifact_readiness`
- `prompt`: first-pass prompt
- `expected_behavior`: plain-language success behavior
- `first_pass_acceptance`: structured acceptance criteria
- `retry_conditions`: null, generic, and verification retry prompts
- `checks`: deterministic and human-judged checks
- `metadata`: source, privacy, difficulty, and version

Retry prompts must not introduce new substantive information if the goal is to measure recoverability.
