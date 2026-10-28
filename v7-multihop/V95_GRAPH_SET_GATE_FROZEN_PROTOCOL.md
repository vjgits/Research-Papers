# PGER V9.5 frozen graph-set gate experiment (2026-10-28)

## Motivation and prior art
ScalableRAG (Hasson et al. 2026, arXiv:2607.25135) uses persistent typed document sets, set algebra and negative-partition diagnostics. These are prior art. This study is a **narrow graph-set gate**, not an implementation of ScalableRAG's full agentic workspace and not a novel algorithm claim. The previous V9.5 synthetic set-workspace unit tests are **not retrieval evidence**.

V9.4 improved MuSiQue but regressed 2Wiki on fixed public question IDs 40:160. Hypothesis: preserve V7.1's top-five source-chain ranking when its induced title-mention graph contains a connected component of at least three documents with at least two edges; otherwise use V9.4 expanded Ettin reranking. This unsupervised criterion is fixed before inspecting IDs 160:240. It may be wrong; no gold labels may enter the gate.

## Frozen test
* Official SAG2 public corpus release 5ec05b38deecc3318bb432c69865959c56058990, 11,656 MuSiQue and 6,119 2Wiki unique documents.
* New question indices 160:240 (80 per dataset), disjoint from V9.3/V9.4's 0:160; public benchmark, **not sealed independent test**. Do not tune on these outcomes.
* Models and candidate generation identical to V9.4: cross-encoder/ettin-reranker-17m-v1, first 32 scored candidates + up to 32 fresh candidates, title+first 1050 chars, max_length=224, CPU two threads.
* Arms: unchanged V7.1 fast; Ettin first-64 fast-tail with first-two anchors protected; Ettin expanded-64 with first-two anchors protected; **V9.5 graph-set gate** choosing unchanged fast when strong graph connectivity, else expanded-64; and gate-fast-tail control choosing unchanged fast when strong, else fast-tail-64.
* For each question, construct named in-memory sets of fast Top-5 document IDs, graph-linked positive subset and unlinked negative subset. Retain both sets in per-query traces. Gate checks only graph topology, never gold or dataset name.
* Compare complete evidence-chain @5/@10, by 2/3/4 supporting documents, recall @5/@10, paired bootstrap 95% CI against V7.1 and same-budget reranker controls, per-query CPU and query count, candidate upper bounds. Score all CE arms physically for counterfactual comparisons. Gate deployment inference savings are **estimates**, not direct benchmark timings.
* Maximum two additional lexical expansion queries per question, 64 CE scoring pairs per full CE arm, no paid APIs, no scheduled or recursive jobs, no main modifications. GitHub workflow is a finite one-time push event on this feature branch.
* A positive result requires no significant easy-question regression and paired improvements over **both** unchanged V7.1 and same-budget control, including credible nonzero four-document recovery; otherwise retain as negative result. Never compare these retrieval-only AE scores directly to ScalableRAG answer accuracy.
