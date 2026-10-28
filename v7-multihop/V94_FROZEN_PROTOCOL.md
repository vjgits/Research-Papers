# PGER V9.4 frozen efficient open-weight reranker comparison

Purpose: Compare **cross-encoder/ettin-reranker-17m-v1** against previously frozen **cross-encoder/ms-marco-MiniLM-L6-v2** (V9.3) on **identical** SAG2 released corpus / question IDs, 64 source passages scored per question, same passage length, same rescue queries, same first-two protection options. No paid APIs or recurring jobs.

## Independent model-choice rationale
The 17.6M-parameter Ettin reranker is Apache 2.0 and its publisher reports 267.4 query-passage pairs/sec on an Intel i7-13700K versus 143.9 for 22.7M-parameter MiniLM-L6, with stronger average MTEB retrieval ranking quality in the source model card. **Those are not PGER multi-hop results** and hardware differs from GitHub. Publisher model card: https://huggingface.co/cross-encoder/ettin-reranker-17m-v1. Ettin was selected on general published benchmarks **before inspecting V9.3 development/confirmation scores**, avoiding outcome-driven reranker selection on this cohort.

## Study
- New development branch `v94-efficient-ettin-evidence-ranker-2026-10-28` isolated from main, base V9.3.
- Exact same code copied from `benchmark_v93.py` with only checkpoint name, result path and resolved revision logging changed.
- Data: official fixed `osunlp/HippoRAG_2` SAG2 corpus release `5ec05b38deecc3318bb432c69865959c56058990`. Public MuSiQue and 2Wiki 40 development + 120 confirmation questions per dataset.
- Four CE variants: fast64 with/without two protected anchors and semantic source-seeded expansion64 with/without anchors; unchanged V7.1 fast baseline. Score **32 first-stage + 32 second-stage = 64** passages for either CE arm; physical test runs extra for paired comparisons. Report full evidence-chain @5/@10, 2/3/4 supporting sources, candidate upper bounds, CPU inference / indexed search costs, CIs. No semantic relation truth verification or answer reader.
- External SAG2 JEV model not independently executed. Do **not** claim best-in-class, algorithmic novelty or real 5–8 hop success based on any model swap.
- If Ettin succeeds, consider a *genuine* cost-aware early-exit implementation with independent locked cohort; if it fails, preserve negative result. Publication claims require new method and independent confirmation.

Finite one-time GitHub Action only, no clock scheduling or autonomous continuation. Source model full revision hash logged after load if available. Do not tune using confirmation samples.
