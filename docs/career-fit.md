# Career fit: Python, search, and data foundations

TraceFind demonstrates Python backend and retrieval fundamentals: a versioned corpus, deterministic lexical ranking, an offline relevance evaluator, a read-only search API, and source labels on returned documents. It is a small component relevant to search and retrieval workflows. It does not use embeddings or an LLM, generate answers, or establish professional experience or eligibility for any role.

## Current examples checked November 9, 2026

Capgemini's careers page lists a **Junior Python Developer** role in Iasi. The description includes Python software components, APIs and backend services, unit testing, documentation, deployment support, and relational databases. The same posting asks for a minimum of two years of overall IT experience, including one year of hands-on Python development, plus French and English. This is a skills reference only; the title does not make it an entry-level match for a particular candidate. Check the live [Capgemini posting](https://careers.capgemini.com/job/Iasi-Junior-Python-Developer/1427338033/) for changes.

Showpad's careers page lists an **AI Engineer** role in Bucharest. It names Python, cloud platforms, LLMs, and RAG, and describes search algorithms and evaluation as preferred experience. TraceFind is relevant only to the lexical retrieval and evaluation foundations: it has no AI model, embeddings, cloud service, or RAG answer generation. The role also requires hands-on AI/LLM experience, so this project alone does not establish that requirement. See the current [Showpad posting](https://job-boards.greenhouse.io/showpad/jobs/8264241).

## How to present TraceFind

Explain that BM25 and overlap are ranking methods, then describe their limits with paraphrases and queries that have no answer in the corpus. Be clear that scores are ranking signals rather than confidence. Discuss how source labels let a caller inspect the retrieved text and why an independent answer-generation step is outside the project. The dataset is synthetic, AI-authored, small, and has no held-out split; report only actual measured results and do not claim generalization.

Use the [interview guide](interview-guide.md) resume drafts only after confirming that each bullet matches your contribution. Be transparent about AI assistance and prepared to explain or modify the implementation yourself.
