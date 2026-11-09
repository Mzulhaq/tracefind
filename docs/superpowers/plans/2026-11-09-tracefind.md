# TraceFind Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publish a working search API with honest, reproducible relevance evaluation for November 9, 2026.

**Architecture:** Validated corpus -> atomic SQLite snapshot -> shared pure-Python ranker -> read-only FastAPI. Offline evaluator compares the same ranker and baseline using fixed graded relevance cases.

**Tech Stack:** Python 3.11+, FastAPI, SQLite, pytest, Ruff, Docker, GitHub Actions.

**Spec:** `docs/design.md`. User has delegated defaults and authorized full execution without a new approval gate.

## Global constraints

- 1-500 documents, <=1,000,000 total characters; 2 MiB input JSON.
- Query <=512 characters, k1=1.2, b=0.75, k integer1..20.
- No paid models, network retrieval, or simulated AI; retrieval scores are not confidence.
- Keep every change within this new repository; no modifications to existing projects.

## Review focus

- Tied ranks and corpus input order must not change metrics (ranking/evaluation tests).
- Invalid relevance labels must fail loudly rather than inflate scores (evaluation tests).
- Unanswerable cases must be separated from answerable averages (evaluation tests).
- Stale or simultaneous replacement must not overwrite silently (store concurrency tests).
- Search revision and returned texts must come from one snapshot (store/API tests).

## Task 1: Ranking and evaluation worker

Own `src/tracefind/retrieval.py`, `evaluation.py`, `tests/test_retrieval.py`, `test_evaluation.py`. Exact interfaces in spec.

- [x] Write failing tests for score/metric math, invalid input, duplicates, deterministic ordering, empty hits and no-answer cases.
- [x] Implement fixed BM25 and distinct-token baseline plus validated evaluator; run owned tests and Ruff.

## Task 2: Store and API primary

Own `models.py`, `store.py`, `api.py`, `cli.py` and corresponding tests. Store replace returns `{revision,count,changed}`; snapshot returns `(revision,documents)`. API consumes ranker `{id,score}` and joins exact body/source from the same snapshot.

- [x] Write failing durable replacement, rollback and concurrent CAS tests; implement validated documents and transactional store.
- [x] Write failing API/CLI tests; implement read-only HTTP surface and operator CLI.

## Task 3: Fixed dataset and documentation worker

Own `data/corpus.json`, `data/queries.json`, `data/README.md`, `docs/interview-guide.md`, `docs/career-fit.md`.

- [x] Author original corpus and labels before running retrieval; do not tune to scores.
- [x] Explain dataset limits/attribution, interview answers, two resume drafts and exercise.

## Task 4: Integrate, review, publish primary

- [x] Run loopback HTTP demo, fixed evaluation and failure analysis; write actual results and README.
- [x] Verify suite/lint/build/clean install and add CI/container checks.
- [x] Independent review, material fixes and regression tests.
- [ ] Scan publication files, verify GitHub identity, create/push once, verify CI and update ledger.
