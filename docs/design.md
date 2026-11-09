# TraceFind design

TraceFind adds retrieval evaluation to a Python/backend portfolio that already covers webhooks and ingestion. It retrieves original synthetic support runbooks, without an LLM, embeddings, paid services, external calls, or generated answers. Lexical retrieval is a real component used in search/RAG, not a simulated model. This small implementation favors explainable behavior over production scale.

## Data and storage

One SQLite database holds one current corpus. A document is a dictionary with exactly `id`, `title`, `body`, `source`. IDs are 1-64 ASCII letters/digits/dot/dash/underscore. Other fields are nonblank strings, title <=160 characters, body <=8000, source <=200; source is an opaque citation label, never fetched. Corpus has 1-500 unique documents and <=1,000,000 total field characters. JSON file limit is 2 MiB. Sort by ID for canonical JSON/SHA256, so input ordering does not change revision. No text normalization occurs before content hashing.

`Store(path).replace(documents, expected_revision=None)` validates before starting BEGIN IMMEDIATE, then atomically replaces all documents and revision. If expected_revision is supplied and differs from current revision (None for empty DB), raise Conflict. This is compare-and-swap, including when the requested content matches the current corpus. Identical content returns unchanged status. `snapshot()` reads revision and all documents in one read transaction and returns `(revision_or_None, list[dict])`. No in-memory cache; each search works on one immutable in-process snapshot. Separate connections per operation, file DB required, foreign schemas rejected using application_id/user_version. Writes are local CLI only; the HTTP API is read-only and binds loopback by default.

## Ranking

`rank(documents, query, *, method='bm25', k=5) -> list[dict]` returns only `{id, score}`. Tokenization: Unicode NFKC then casefold, Unicode letters/digits separated by nonword or underscore; no stemming, stopword removal, or synonym expansion. Document text is title + space + body, no title boost. Query terms are unique, at most 512 characters; k is integer 1..20, methods bm25/overlap. Ignore zero scores; deterministic tie break by ID. Reject invalid method, duplicate IDs, invalid k/query. Empty or punctuation-only query produces no hits. Tokenization and ranking are identical offline and in API.

BM25 uses k1=1.2,b=0.75, positive idf `log(1+(N-df+0.5)/(df+0.5))`; score is sum over unique query terms of idf * tf*(k1+1)/(tf+k1*(1-b+b*dl/avgdl)). Empty documents contribute no score. Baseline score counts distinct query tokens present in each document. All parameters/tokenization are included in evaluation metadata. Linear scanning and per-request index construction suit <=500 documents; no throughput claims.

## API and CLI

`create_app(db_path)` owns no global mutable database connection. GET /health: ok even without corpus. GET /v1/corpus: revision and count. GET /v1/search?q=...&k=5&method=bm25: revision, query, method, hits each with id/title/source/text/score. Returned text equals the complete stored body for citation inspection. Empty corpus returns 409, invalid parameters 422, read failure 503 with generic message. No HTTP write endpoints, no auth, rate limits, access control or production deployment; use synthetic/public data locally. Search scores are ranking signals, never confidence probabilities or answers.

CLI: `tracefind --db PATH load data/corpus.json [--expected-revision SHA]`; `tracefind --db PATH search QUERY [--method bm25|overlap] [--k N]`; `tracefind evaluate --corpus data/corpus.json --queries data/queries.json [--k 3]`; `tracefind --db PATH serve [--host 127.0.0.1] [--port 8000]`. CLI prints JSON except serve; exit1 operational/validation error, exit2 stale revision conflict. JSON parsing rejects duplicate keys and nonfinite values. No secrets or environment configuration required.

## Evaluation

`evaluate(documents, cases, *, k=3) -> dict`. Cases exactly `{id,query,relevant}` with unique case ID, query, and relevant mapping known document IDs -> integer grades 1..3; empty relevant means unanswerable. Validate every case before scoring, reject unknown IDs/duplicate case IDs/noninteger or invalid grades/empty suite. For answerable cases, macro-average recall@k (#relevantretrieved/#relevant), reciprocal rank@k of first relevant, nDCG@k with gain 2^grade-1 and log2(rank+1), ideal ranking over all relevant docs. Unanswerable cases excluded from relevance averages and separately report empty-result rate and false-positive count. Per-query rankings, metrics, and failure cases included. Never interpret no-empty output as proof of answerability. Duplicate predictions cannot inflate metrics.

Dataset: 20 original fictional HarborDesk runbooks, 24 labeled queries including 20 answerable (some multi-relevant/graded and paraphrases) and 4 unanswerable. Write before looking at scores; disclose AI-authored toy data, no independent human judgments, and no held-out split. Report actual metrics, including regressions/failures, without tuning labels or asserting BM25 must win. Output deterministic, no timestamps or timing benchmarks, includes corpus/query content hashes and ranking policy.

## Delivery

Tests prove exact ranking/metric math, empty cases, invalid inputs, order stability, durable snapshots, CAS concurrency, rollback, API citations and CLI behavior. Real loopback HTTP demo loads synthetic corpus, queries both methods, checks citations/revision, and prints actual evaluation. CI tests Linux+Windows Python3.11 and Linux3.13; Docker demo runs non-root and network-disabled except loopback. Documentation includes setup, architecture, tradeoffs, actual evaluation and error analysis, career sources, AI assistance, interview notes and a small exercise. Publish Mzulhaq/tracefind after checks and independent review; verify remote commit/CI and record weekly ledger.
