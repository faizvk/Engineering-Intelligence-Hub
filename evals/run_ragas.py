"""Generation metrics with RAGAS, judged by Claude + embedded by Voyage.

The RAGAS quickstart uses OpenAI; we swap in Claude (judge) + Voyage (embeddings)
via the LangChain wrappers to stay consistent with the stack. NOTE: Claude 4.x
removes temperature — do NOT pass temperature=0 (it 400s); pin determinism via
a fixed model + low effort instead.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.settings import get_settings

GOLDEN = Path(__file__).parent / "datasets" / "golden.jsonl"

# RAGAS metric -> result key.
_METRIC_KEYS = [
    "context_recall",
    "llm_context_precision_with_reference",
    "faithfulness",
    "answer_relevancy",
    "factual_correctness",
]


def run(limit: int | None = None) -> dict[str, float]:
    from langchain_anthropic import ChatAnthropic
    from langchain_voyageai import VoyageAIEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        FactualCorrectness,
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    from backend.rag.service import answer_query

    s = get_settings()
    # Sonnet is a strong, cheap judge. No temperature kwarg on 4.x.
    judge = LangchainLLMWrapper(
        ChatAnthropic(
            model=s.model_workhorse,
            max_tokens=2048,
            api_key=s.anthropic_api_key.get_secret_value(),
        )
    )
    judge_emb = LangchainEmbeddingsWrapper(
        VoyageAIEmbeddings(model=s.embed_model, output_dimension=s.embed_dim)
    )

    rows = [
        json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if limit:
        rows = rows[:limit]

    samples = []
    for row in rows:
        out = answer_query(row["question"])
        samples.append(
            {
                "user_input": row["question"],
                "retrieved_contexts": out.contexts,
                "response": out.answer,
                "reference": row["ground_truth"],
            }
        )

    result = evaluate(
        dataset=EvaluationDataset.from_list(samples),
        metrics=[
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
            Faithfulness(),
            ResponseRelevancy(),
            FactualCorrectness(),
        ],
        llm=judge,
        embeddings=judge_emb,
    )
    print(result)
    result.to_pandas().to_csv(Path(__file__).parent / "ragas_latest.csv", index=False)

    scores: dict[str, float] = {}
    for key in _METRIC_KEYS:
        try:
            scores[key] = float(result[key])
        except Exception:
            pass
    return scores


if __name__ == "__main__":
    run()
