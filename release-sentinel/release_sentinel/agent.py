from __future__ import annotations

import json
from pathlib import Path
import os
from typing import Literal

from openminion import Agent, AgentOutputValidationError, ProviderError, tool
from pydantic import BaseModel, Field

from release_sentinel.audit import inspect_repository


class Finding(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str
    evidence: str
    recommendation: str


class ReleaseAssessment(BaseModel):
    decision: Literal["ready", "ready_with_caveats", "not_ready"]
    summary: str
    confidence: float = Field(ge=0, le=1)
    findings: list[Finding]
    verification_gaps: list[str]
    next_actions: list[str]


def build_agent(root: str | Path, session_id: str | None = None) -> Agent:
    resolved_root = Path(root).expanduser().resolve(strict=True)

    @tool(
        name="inspect_repository",
        description="Collect read-only repository metadata and release readiness indicators. Never reads file contents or executes project code.",
        idempotent=True,
        tags=("repository", "release-readiness", "read-only"),
    )
    def inspect_release_repository() -> str:
        return inspect_repository(resolved_root).to_json()

    instructions = """You are Release Sentinel, a careful release-readiness reviewer.
Use inspect_repository before making an assessment. Base claims only on returned evidence. Do not imply tests passed: this tool detects test-related files but does not execute tests. Do not infer that dependencies are secure, that CI passed, or that documentation is accurate from file presence alone. Treat names like .env or token-containing paths as risk indicators, not proof of leaked secrets. Distinguish observed facts from uncertainty. Return a conservative assessment: not_ready when evidence suggests a serious release blocker; ready_with_caveats when material verification is missing; ready only when evidence supports readiness. Findings must be actionable and refer to concrete evidence. Keep the result concise and useful."""

    return Agent(
        name="release-sentinel",
        instructions=instructions,
        output_type=ReleaseAssessment,
        tools=[inspect_release_repository],
        forced_tools=["inspect_repository"],
        session_id=session_id,
        config_path=os.environ.get("OPENMINION_CONFIG_PATH") or None,
    )


def run_review(root: str | Path, session_id: str | None = None) -> ReleaseAssessment:
    prompt = (
        "Review this repository for release readiness. Inspect the repository, "
        "identify concrete risks and missing verification, and recommend the "
        "smallest useful next actions. Return a structured assessment."
    )
    with build_agent(root, session_id=session_id) as agent:
        result = agent.run(prompt)
    if not isinstance(result.output, ReleaseAssessment):
        raise AgentOutputValidationError("OpenMinion returned no validated ReleaseAssessment", raw_text=result.text)
    return result.output


def assessment_json(assessment: ReleaseAssessment) -> str:
    return json.dumps(assessment.model_dump(mode="json"), indent=2, sort_keys=True)
