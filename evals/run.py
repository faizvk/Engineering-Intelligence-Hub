"""The CI quality gate. Fails the build when a change regresses answer quality.

    python -m evals.run --suite ci --fail-under-faithfulness 0.85 --fail-under-recall 0.80

Deterministic retrieval metrics gate hard; the LLM-judged RAGAS slice is kept
small (a frozen ~25-row CI subset) and its thresholds sit a little below current
scores to absorb judge noise. The full nightly suite drops the limit.
"""

from __future__ import annotations

import argparse
import sys

from core.tracing import configure_langsmith
from evals.run_retrieval import main as retrieval_main


def main() -> int:
    ap = argparse.ArgumentParser(description="RAG eval / quality gate")
    ap.add_argument("--suite", default="ci", choices=["ci", "full"])
    ap.add_argument("--fail-under-faithfulness", type=float, default=0.85)
    ap.add_argument("--fail-under-recall", type=float, default=0.80)
    args = ap.parse_args()

    configure_langsmith()
    failures: list[str] = []

    retr = retrieval_main()
    if retr["recall@5"] < args.fail_under_recall:
        failures.append(f"recall@5 {retr['recall@5']:.3f} < {args.fail_under_recall}")

    from evals.run_ragas import run as ragas_run

    scores = ragas_run(limit=25 if args.suite == "ci" else None)
    faith = scores.get("faithfulness", 0.0)
    if faith < args.fail_under_faithfulness:
        failures.append(f"faithfulness {faith:.3f} < {args.fail_under_faithfulness}")

    if failures:
        print("QUALITY GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("QUALITY GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
