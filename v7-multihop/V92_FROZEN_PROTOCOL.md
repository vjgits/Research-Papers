# V9.2: Finite full-corpus evidence expansion trial — frozen protocol

Branch `v92-fullcorpus-evidence-expansion-2026-10-28`, forked from completed V7.1 on SAG2 official corpus. Main untouched. No paid APIs, no reviewer agents, no recurring jobs.

## Why this experiment before heavier models
SAG2 retrieves from original question, scores likely necessary evidence, selects terms grounded in source passages, follows those terms to other passages, and re-scores. This experiment isolates the cheap **source-term expansion** part using lexical retrieval and ranked source witnesses, without JEV. The method resembles published pseudo-relevance feedback and SAG2, so it is NOT a PGER original primitive. We want to know whether this component helps before paying the cost of larger neural rerankers.

## Dataset, metrics, method
- Exactly released `osunlp/HippoRAG_2` pinned revision `5ec05b38deecc3318bb432c69865959c56058990`: 1000 questions with complete corpora of 6119 2Wiki, 11656 MuSiQue, and 9811 HotpotQA source texts. Gold support not used by retrieval.
- Public datasets inspected across earlier PGER research: not an independent sealed test.
- Dev first 120 per dataset, later confirm next 280 per dataset. Fixed ranking methods frozen before both phases; neither phase supports test-then-edit claim.
- Unchanged BM25 and exact V7.1 offline 1-hop Aho-Corasick graph source code. Eight arms: V7.1, 2 strengths of proper-name expansion, 3 strengths of mixed source-name/rare-term expansion, one repeated-evidence coverage heuristic, one interleave. Source quotes and action parameters recorded; quotes are not semantic entailment.
- Every expansion method receives up to eight distinct **additional BM25 queries for each expansion family** and source witness. V7.1 receives none; CPU is measured. Preserve first 2 V7.1 documents, report full supporting chain and partial gold recall at Top5/10, wins/losses, question-bootstrap confidence intervals, offline indexing.
- A true benchmark comparison with SAG2 is against author's archived scores, not independent JEV run (paid provider). Do not call ours SOTA unless independently replicated superior on same hardware and corpus.

## First iteration stop/pivot
1. Run one-time dev+confirmation with fixed settings, under free GitHub CPU.
2. If no notable recovery or worse Top5, keep V7.1 and do NOT deploy the expansion; next examine local open-weight source-necessity ranker as a separately measured costed alternative.
3. If it improves dev and confirmation on meaningful high-support cases without unacceptable CPU cost, rerun on all 1000 in a separately tracked experiment.
4. Future novelty research still needs verified answer-changing proof gaps; lexical expansion/graph matching are known prior art.

No unlimited recursive workflow; user-approved research execution is bounded to avoid wasted compute.
