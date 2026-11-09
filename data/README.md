# TraceFind evaluation data

`corpus.json` contains 20 original, fictional HarborDesk support runbooks. Each document has exactly `id`, `title`, `body`, and `source`. The bodies cover account access, billing, deployments, incidents, backups, and security; each source is an opaque `handbook://` citation label and does not point to a fetched resource.

`queries.json` contains 24 judgments using exactly `id`, `query`, and `relevant`. Twenty queries are answerable and map relevant document IDs to graded relevance values from 1 to 3. Several cases have multiple relevant documents and use paraphrases of runbook instructions. Four queries are unanswerable: three have lexical overlap with the corpus but ask for facts that are not there, and one concerns an unrelated topic with only incidental common-word overlap.

The documents and labels are an AI-authored synthetic toy dataset. Labels were fixed before scoring and have not been independently human-validated; do not tune them after seeing metrics. There is no held-out split, statistical confidence claim, real user data, or performance claim. This dataset is useful for explaining evaluation mechanics and inspecting individual rankings, not for generalizing to production support search.

Corpus limits and ranking behavior are specified in [the design](../docs/design.md). The evaluator's output includes content hashes so a score can be tied to the exact corpus and judgments used.
