# Release Sentinel

Release Sentinel is a small, evidence-first release readiness agent for the Cortensor Mainnet Full Alpha builder round. It uses the OpenMinion 0.1 Python SDK to run a model-backed assessment over a deterministic, read-only repository inventory. It helps a maintainer spot missing release hygiene and decide what to verify before shipping.

## What it does

- Uses an OpenMinion `Agent` with a registered Python tool and typed Pydantic output.
- Inspects Git status, changed and untracked path names, common package manifests, test indicators, CI workflow indicators, documentation, license files, lockfiles, and suspiciously named changed paths.
- Produces a structured `ready`, `ready_with_caveats`, or `not_ready` decision, findings, verification gaps, and next actions.
- Supports a deterministic evidence-only mode for quick local checks and tests without credentials.
- Does not execute project code, install dependencies, read file contents, or send diffs to the model.

The scanner reports indicators, not proof. Finding a test file does not mean tests pass; finding a CI configuration does not mean CI is green; and a path named `.env` is a warning signal, not proof of a secret leak.

## Requirements

- Python 3.11 or newer
- OpenMinion Python SDK 0.1.x
- A configured OpenMinion model provider for the model-backed review

## Install

Create a virtual environment and install this project:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

To install from the supplied OpenMinion checkout before installing this project, run from the directory containing both repositories:

```bash
python -m pip install -e ./openminion
python -m pip install -e './release-sentinel[test]'
```

Configure OpenMinion using its documented setup flow and verify a provider is configured:

```bash
openminion --version
openminion status readiness
```

Provider credentials should be configured through OpenMinion's supported configuration mechanism. Do not commit credentials or paste them into issue reports. `OPENMINION_CONFIG_PATH` can optionally select a configuration path if supported by your OpenMinion setup.

## Run

Model-backed review:

```bash
release-sentinel /path/to/repository
```

Save the structured report:

```bash
release-sentinel /path/to/repository --output reports/release-review.json
```

Reuse an OpenMinion session when desired:

```bash
release-sentinel /path/to/repository --session release-check-2026-10
```

Run only the deterministic scanner without a model:

```bash
release-sentinel /path/to/repository --evidence-only
```

The model-backed path requires a real configured provider. Evidence-only mode is useful for smoke testing but is not a substitute for the required real model demo.

## SDK workflow

1. The CLI resolves the target directory.
2. `build_agent` creates an OpenMinion `Agent`, registers `inspect_repository` using `@openminion.tool`, and requests a typed `ReleaseAssessment`.
3. The tool gathers repository metadata using read-only Git commands and filesystem names. It does not read source file contents or run shell commands from the model.
4. The tool is forced for the review turn so the model must receive fresh evidence before making claims.
5. OpenMinion validates the model's result against the Pydantic schema. Provider and output-validation failures are surfaced distinctly.
6. The CLI prints JSON and optionally saves it to a report file.

## Tests

```bash
python -m pytest -q
```

The tests exercise the evidence scanner and do not require model credentials. A live model run must be demonstrated separately with a configured OpenMinion provider.

## Demo video plan (2–3 minutes)

1. Show `openminion --version` and `openminion status readiness` with a configured provider.
2. Run `release-sentinel . --evidence-only` and explain the evidence fields.
3. Run `release-sentinel . --output reports/demo-review.json` to demonstrate the real model-backed SDK workflow.
4. Open the JSON report and point out the decision, evidence-grounded findings, and verification gaps.
5. Close with the building blocks exercised and one or two observed rough edges from the actual run. Do not claim a live model run unless the output and provider configuration are visible in the recording.

## Building Blocks Tested

| OpenMinion building block | Usage | Current verification |
|---|---|---|
| Agent execution | `Agent.run` through `run_review` | Covered by implementation; live provider run requires configured credentials |
| Tool registration | `@openminion.tool` repository inventory tool | Scanner and tool registration are in source; live tool invocation must be confirmed in a model run |
| Typed output | Pydantic `ReleaseAssessment` schema | Schema is implemented; live provider output validation requires a model run |
| Sessions | Optional `--session` forwarded to `Agent` | Implemented; continuity across runs not yet claimed |
| Diagnostics/errors | Provider, timeout, and schema errors produce distinct CLI exits | Error paths implemented; provider-specific failure modes need live testing |
| Permissions/safety | Tool is read-only and does not execute user code | Unit tests cover that file contents are not emitted by the scanner |
| Memory, skills, delegation | Not used | Deliberately out of scope for this focused workflow |

## What We Learned

Initial engineering hypotheses to validate during the demo:

- A forced read-only evidence tool can make model claims easier to audit than asking the model to infer repository state from a prompt alone.
- Typed output is useful for repeatable downstream review, but provider/model combinations may vary in schema adherence and tool-call reliability.
- Session reuse should be tested for whether stale release evidence leaks into later assessments; for release checks, fresh evidence should take precedence over conversational memory.
- File-presence heuristics are only signals. A future version should optionally ingest CI/test reports and dependency audit results as explicit evidence, while preserving a clear boundary between observed results and model interpretation.

Replace these hypotheses with actual observations after the live run. For any bug report, include the OpenMinion version, provider/model, reproduction steps, expected and actual behavior, sanitized logs, and a request/run ID when available.

## Security and scope

The scanner does not read file contents and does not invoke project test commands. It can enumerate path names and Git status. Treat repository paths and resulting reports as potentially sensitive. Only point it at repositories you are authorized to inspect. The model receives the collected metadata, including changed path names, so review path names before using it on sensitive repositories.

## License

MIT
