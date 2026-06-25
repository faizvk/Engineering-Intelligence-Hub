# Experiments — Lab Notebook

Each row is a hypothesis, the config that tests it, the score delta, and the
decision. Decide on **quality per dollar**, not raw quality. Run with
`python -m evals.ab_experiment` (retrieval) and `python -m evals.run_ragas`
(generation), against the committed golden set.

| Date | Hypothesis | Config | Metric Δ | Cost/query Δ | Decision |
|------|------------|--------|----------|--------------|----------|
| _tbd_ | Reranking lifts MRR enough to justify the call | hybrid+rerank vs hybrid-only | MRR _tbd_ | +Voyage rerank (~cents) | _tbd_ |
| _tbd_ | Opus only earns its cost on the `difficulty: hard` slice | Sonnet vs Opus on hard rows | faithfulness _tbd_ | +1.7× LLM | _tbd_ |
| _tbd_ | Contextual Retrieval blurbs beat raw chunks | blurb+voyage-3.5 vs voyage-context-3 | recall@5 _tbd_ | +Haiku enrich | _tbd_ |

## How to read it

- **Retrieval MRR** is the headline retrieval number; the reranker should move it
  the most for the least code.
- **Faithfulness** is the trust number; a +0.03 gain for 3× cost usually loses to
  the cheaper config — record that reasoning, it's the senior signal.
- Promote downvoted production answers (LangSmith `user_thumbs=0`) into
  `golden.jsonl`, so the eval set hardens against real failures.
