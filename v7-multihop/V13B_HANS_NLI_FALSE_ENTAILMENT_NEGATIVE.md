# PGER V13B — independent HANS natural-language inference safety gate FAILED

**Date:** 2026-10-28.
**Successful Actions job:** https://github.com/vjgits/Research-Papers/actions/runs/40727262971
**Question-level human-annotated source cases and model errors:** https://github.com/vjgits/Research-Papers/actions/runs/40727262971/artifacts/12832319798
**Isolated branch:** v13b-independent-nli-verifier-gate-2026-10-28, main unchanged.

## Published open-weight model and adversarial source

Model: `cross-encoder/nli-MiniLM2-L6-H768`, Apache-2.0 (Hugging Face SHA `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`). Original training described as SNLI+MultiNLI. Test corpus: HANS, McCoy, Pavlick & Linzen (ACL 2019), MIT dataset, human labeled entailment/non-entailment, specifically designed to expose false inference by lexical overlap/subsequence/constituent heuristics.

One **frozen random seed 20261028** chose 45 entailment + 45 non-entailment examples from each of three heuristic categories, 270 total from 30,000 published test rows. No model finetuning, no user-paid API. Exact dataset SHA256 and all example identifiers/outputs archived. Three-way NLI predicted `contradiction / entailment / neutral`; neutral and contradiction both map to HANS non-entailment. Source class index read from model id2label, not guessed.

## Measured results

| Statistic | MiniLM NLI | Deliberately naive lexical control |
|---|---:|---:|
| Balanced accuracy | 64.815% | 50.00% |
| Entailment precision | 58.696% | 50.00% |
| Entailment recall | 100% | 100% |
| False-positive accepting **non-entailment** | **95/135 = 70.370%** | 135/135 = 100% |
| Lexical-overlap false entailment | 13/45 = 28.889% | 100% |
| Subsequence false entailment | 37/45 = 82.222% | 100% |
| Constituent false entailment | 45/45 = 100% | 100% |

Inference 270 examples CPU process-time batch amortized **11.625 ms/pair** on hosted CPU, model load 1.259 CPU sec separate. Does not include remote model weight download or serving. Reliability criteria frozen BEFORE seeing outputs: entailment precision >=90%, recall >=75%, overall false-positive rate <=10%, and EACH heuristic group false-positive rate <=10%. All three specificity requirements FAILED.

## Scientific interpretation

This is a decisive negative result for using **this particular MiniLM checkpoint as a proof verifier under HANS-like traps**. We do not claim all NLI models are incapable, and we do not conflate HANS premise-hypothesis label accuracy with PGER multi-document source validity. Yet HANS is an appropriate conservative stress test to disallow a verifier that falsely accepts most adversarial non-entailment cases.

**Promotion prohibited:** Do not integrate into source-edge proof gate, do not answer verified based on this model. Independent human-validated, domain-specific source-span + typed logical fact annotations are required, with contradiction/unknown handling and calibration/failure-to-abstain measures. More pretrained model swapping on the SAME known HANS confirmation subset would constitute test-set selection and must be labeled exploratory or run on a fresh preregistered sample.

This outcome reconciles V13A: co-necessary gold source pairs are not factual entailment. V13A pair selector hurt overall retrieval and 4-support performance. Retain boosted PGER as best within-corpus retrieval component; keep all unsupported relations unverified.

Next code-only safety work can add a **fail-closed proof/evidence ledger** that requires an independently authorized external validator and exact quotes/hashes, rejects contradiction and missing links, and otherwise abstains. Such unit tests of logical safeguards must NOT be portrayed as measured truth, end-to-end answer correctness or publishable multi-hop superiority.

All failed V8–V13 work and V11.3/11.4 positives preserved; no scheduling, background jobs, paid APIs, merging or main writes.
