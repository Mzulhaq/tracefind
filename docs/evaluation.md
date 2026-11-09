# Fixed retrieval evaluation

Measured on November 9, 2026 using Python 3.11.9, the committed synthetic corpus, and the labels frozen before scoring. Reproduce with:

```bash
tracefind evaluate --corpus data/corpus.json --queries data/queries.json --k 3
python scripts/check_evaluation.py
```

The [full JSON report](evaluation.json) includes every ranking, label, failure, and metric. It records canonical-content SHA256 values (not raw-file byte hashes):

- Corpus: `8e113de9191ea4bb9dc427da705d8cbdad37f8a2fb496b3770bcbe4692f1cd8b`
- Cases: `b36e32705f4fcf73be6981133537cec6e0300422ee70cc797d6c0878c9fbb35a`

Document/case ordering and JSON whitespace do not affect these identities. No labels or document wording were changed after observing scores.

## Results at k=3

| Method | Macro recall | MRR | nDCG | Unanswerable queries with hits | Unanswerable empty-result rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Distinct-token overlap baseline | 0.650000 | 0.925000 | 0.779825 | 4 / 4 | 0.000000 |
| BM25 | 0.675000 | 0.950000 | 0.836360 | 4 / 4 | 0.000000 |

The first three metrics average only the 20 answerable cases. The final two use only the four unanswerable cases. A false positive here means a query labeled unanswerable received at least one hit, rather than counting individual returned documents. Metric values in JSON are rounded to 12 decimal places; the table rounds to six. Corpus size is 20 documents. These are relevance measurements on this fixed toy set, not throughput or user-impact measurements.

## Error analysis

- **q03, login lockout:** BM25 puts suspicious-login guidance above the intended lockout procedure. Its nDCG is 0.496639 versus the baseline's 0.787155. BM25 does not improve every query.
- **q04, invoice download:** BM25 ranks the invoice-copy document first and retrieves both labeled relevant documents, giving recall 1.0 versus baseline 0.5. The baseline's tied scores prefer the card-update document by ID; weighted terms distinguish this example better.
- **q06, refund status:** Both methods rank password-reset guidance first and the intended refund document second. Common language such as “sent,” “has,” and “been” can dominate a short natural-language question. Neither method understands the task or expands vocabulary semantically.
- **q17, authorized workspace export:** BM25 ranks invoice-copy guidance first, labeled only weakly relevant (grade 1), and the grade-3 export document second. MRR still reports 1.0 because it ignores relevance grades. nDCG is 0.709810, exposing the ordering problem. The weak invoice label itself is subjective and deserves independent human review before any broader claim.
- **q19, incident follow-up:** BM25's recall is 0.5 versus baseline 1.0, but its nDCG is higher because it promotes the grade-3 postmortem guidance. Recall and graded ordering measure different aspects of search.
- **q21–q24, unsupported questions:** Both methods return results for all four cases. q21 retrieves tax-invoice guidance with a high BM25 score (18.119845), but the handbook does not specify the requested procedure for adding VAT registration to an issued invoice. q24 asks about a lobby fern; shared function words still yield matches. A score threshold chosen from these few cases would not establish reliable answerability detection.

## What these results support

The implementation demonstrates a reproducible comparison, graded relevance metrics, and inspectable failure cases. The dataset and labels are AI-authored, fixed before scoring, and not independently human-validated. There is no held-out split, human inter-rater agreement, statistical uncertainty estimate, or claim that these gains generalize. It tests lexical retrieval only; there is no model answer quality, embedding quality, or hallucination benchmark.

A useful next experiment would freeze a separate set of paraphrases, define the expected judgments independently, and compare a specific change such as stopword filtering. Keep the original results and record new dataset/policy hashes. Adding an LLM or changing labels to make this table look better would not resolve the current evaluation limits.
