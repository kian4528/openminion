from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_sentinel.audit import inspect_repository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release-sentinel",
        description="Run an evidence-first release readiness review with OpenMinion.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository directory to review")
    parser.add_argument("--session", default=None, help="Optional OpenMinion session ID")
    parser.add_argument("--evidence-only", action="store_true", help="Run the deterministic scanner without a model")
    parser.add_argument("--output", type=Path, help="Write the result to a JSON file")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.evidence_only:
            output = inspect_repository(args.path).to_json()
        else:
            from openminion import AgentOutputValidationError, ProviderError, TurnTimeoutError
            from release_sentinel.agent import assessment_json, run_review

            try:
                assessment = run_review(args.path, session_id=args.session)
            except ProviderError as exc:
                print(f"OpenMinion provider error [{exc.code}]: {exc.message}", file=sys.stderr)
                print("Check your OpenMinion provider/model configuration and credentials.", file=sys.stderr)
                return 3
            except AgentOutputValidationError as exc:
                print(f"model output did not match the assessment schema: {exc}", file=sys.stderr)
                return 4
            except TurnTimeoutError as exc:
                print(f"OpenMinion run timed out: {exc}", file=sys.stderr)
                return 5
            output = assessment_json(assessment)
    except ImportError as exc:
        print(f"OpenMinion SDK could not be loaded: {exc}", file=sys.stderr)
        print("Install the OpenMinion 0.1.x SDK and its dependencies before a model-backed run.", file=sys.stderr)
        return 6
    except FileNotFoundError as exc:
        print(f"repository path not found: {exc}", file=sys.stderr)
        return 2
    except NotADirectoryError as exc:
        print(f"repository path is not a directory: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"invalid repository: {exc}", file=sys.stderr)
        return 2

    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"report written to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
