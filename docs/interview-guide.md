# TraceFind interview guide

TraceFind is a small lexical retrieval system with an offline evaluation set and a read-only HTTP search interface. It uses no LLM, embeddings, generated answers, or external search service. Discuss the actual retrieval and evaluation behavior rather than implying a full RAG or AI application.

## Architecture questions and answers

### What happens between loading a corpus and returning search results?

The CLI validates a JSON corpus, computes a canonical revision from documents sorted by ID, and asks SQLite to replace the current corpus in one `BEGIN IMMEDIATE` transaction. A caller may provide an expected revision for compare-and-swap protection. Each search reads one database snapshot and ranks against that snapshot. The HTTP API exposes read-only health, corpus metadata, and search routes; loading or replacing documents is a CLI operation.

### How is text tokenized?

Text is normalized with Unicode NFKC, casefolded, and split into Unicode letter and digit runs. Underscores and other non-word boundaries separate tokens. The ranker does not remove stop words, stem terms, or expand synonyms. Each query is limited to 512 characters and query terms are unique. Title and body are combined without a title boost.

### What do the two ranking methods measure?

The overlap baseline counts distinct query tokens present in a document. BM25 uses the configured constants `k1=1.2` and `b=0.75`, with positive inverse document frequency `log(1 + (N - df + 0.5) / (df + 0.5))`. Both ignore zero-score documents, return only ranked hits, and break score ties deterministically by document ID. Scores order documents; they are not probabilities or confidence that a passage answers a question.

### What do the evaluation metrics mean?

For the 20 answerable cases, evaluation macro-averages recall@k, reciprocal rank@k of the first relevant result, and nDCG@k. Recall divides retrieved relevant documents by all relevant documents for that case. nDCG uses gain `2^grade - 1` for grades 1–3 and discounts by `log2(rank + 1)`, with an ideal ordering over all judged relevant documents. The four unanswerable cases are reported separately with empty-result rate and false-positive count. They are not included in answerable relevance averages.

### What are the dataset's limitations?

The corpus and labels are an AI-authored synthetic fictional toy set, not real support logs. Labels were fixed before scoring and have not been independently human-validated. There is no held-out split, so these scores do not establish generalization. Lexical methods miss synonyms and paraphrases when terms differ; they can also retrieve documents that share terms but do not answer the question. The unanswerable labels are useful checks, not proof that a system can determine answerability. One unanswerable query concerns an unrelated topic with only incidental common-word overlap. No timing or throughput benchmark is claimed.

### Why use SQLite compare-and-swap and a single corpus?

Atomic replacement prevents readers from seeing a partially loaded corpus. An expected revision lets an operator detect that another update changed the corpus before replacement. Each operation owns its own connection and search uses a consistent snapshot. This local design keeps behavior understandable for a small portfolio project; it does not provide multi-tenant indexing, distributed coordination, auth, rate limiting, or production deployment controls.

### How are citations represented?

Search hits include the complete stored body and its opaque `source` label so a caller can inspect the retrieved text. The source is data for citation display; the service does not fetch it. Returning a document is not the same as generating a grounded answer, and TraceFind does not synthesize a response.

## 30-minute exercise: add five frozen paraphrase cases

Choose five answerable questions that express existing runbook guidance in different words. Write each query and its graded relevant-document IDs before running either ranking method. Add the cases to a separate candidate file, confirm their schema, then measure and inspect the rankings. Record the corpus and candidate-file hashes, all metric changes, and any false positives. Keep the original 24-case file unchanged so comparisons remain reproducible.

Hints: target a few different topics, avoid copying phrases verbatim from titles, and include at least one multi-relevant question. A useful answer note should explain whether a missed result reflects vocabulary mismatch, ranking order, or a mistaken judgment. Do not revise relevance labels simply to improve a score; any correction should have independent evidence and be recorded as a new dataset revision.

## Resume drafts

These are factual starting points, not claims about measured impact. Adapt them to your actual contribution after you can explain and demonstrate the code.

- Built a Python lexical retrieval service with BM25 and token-overlap ranking, revisioned SQLite corpus loading, and citation-bearing search results.
- Created a graded synthetic evaluation set with answerable and unanswerable cases and reported recall@k, reciprocal rank, nDCG, and false-positive behavior.

AI assistance contributed to this project and its synthetic data. Describe your own work accurately, disclose that assistance when relevant, and avoid implying LLM, embedding, or generation features.
