# Verification evidence

Local checks on November 9, 2026 used Windows and Python 3.11.9.

| Command/check | Observed result |
| --- | --- |
| `python -m pytest --cov=tracefind --cov-report=term-missing` | 68 tests passed; 95% statement coverage. |
| `python -m ruff check .` | Passed. |
| `python -m ruff format --check .` | Passed. |
| `python scripts/demo.py` | Real loopback HTTP demo passed: 20 documents, 24 evaluation cases, matching API/offline ranks, exact source text, and stable revision on identical reloading. |
| `python scripts/check_evaluation.py` | Reproduced the frozen report within numeric tolerance 1e-12. |
| Independent evaluation with `PYTHONHASHSEED=1,2,1000` | Byte-identical evaluation JSON in all three processes. |
| `python -m build` | Source distribution and wheel built successfully. |
| Fresh virtual environment: install `requirements.lock`, then the wheel with `--no-deps` | Installation passed; installed entry point, real HTTP demo, and frozen evaluation check passed. |
| `python -m pip check` in the fresh environment | No broken requirements. |

The tests cover ranking/graded metric math, invalid judgments, duplicate predictions, ties and normalization, transaction rollback after an injected SQL failure, simultaneous compare-and-swap writers, concurrent snapshots, source citations, API error codes, and bounded/strict JSON ingestion. The independent AI-assisted review reran the suite, HTTP demo, and evaluation and found no material defects at that stage.

The final follow-up unified ingestion/ranking validation and added regressions for the exact corpus character bound including IDs and invalid Unicode. Frozen evaluation results remained unchanged. The independent reviewer checked the follow-up and final error-analysis claims and found no remaining material issues.

Docker is unavailable on the local host. [GitHub Actions run 42633617255](https://github.com/Mzulhaq/tracefind/actions/runs/42633617255) verified source commit `3bd459a11532ef859623279d986aeb6ce6442ade`: all four jobs passed. Python 3.11 ran on Windows and Linux, and Python 3.13 ran on Linux, including the tests, lint/format checks, HTTP demo, frozen evaluation, package build, and dependency checks. The container job built the Dockerfile and passed `docker run --rm --network none tracefind`, including its loopback HTTP requests. There are no claimed production, latency, throughput, or hiring outcomes.
