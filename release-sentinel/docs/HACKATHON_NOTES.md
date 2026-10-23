# Hackathon Submission Notes

## Project

Release Sentinel: evidence-first release readiness review with OpenMinion 0.1.x.

## Submission checklist

- [x] Public-repository-ready source layout and setup/run README
- [x] OpenMinion SDK is used in the runtime through `Agent`, `@tool`, and typed output
- [x] Repeatable repository inventory workflow
- [x] Deterministic tests that do not require provider credentials
- [x] Building Blocks Tested note
- [x] What We Learned section with hypotheses clearly marked for validation
- [ ] Real model-backed demo recording
- [ ] Replace learning hypotheses with actual observed run results
- [ ] Publish repository and attach 1–5 minute demo video to the hackathon PR

## Known limitations before live validation

- The model-backed run cannot be verified until a provider is configured in OpenMinion.
- The scanner checks repository indicators but does not execute tests or verify CI state.
- The tool is deliberately read-only and avoids source contents; this limits the depth of code-level review.
- No claim is made yet about Portal or Gemma4 access.
