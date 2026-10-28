# PGER V13C — fail-closed proof-gap ledger; safety mechanism tests PASSED, truth NOT established

Date: October 28, 2026.
Successful corrected one-time GitHub Action: https://github.com/vjgits/Research-Papers/actions/runs/40727908482
Earlier smoke-run failure: https://github.com/vjgits/Research-Papers/actions/runs/40727792216
Isolated branch: v13c-fail-closed-proof-ledger-2026-10-28; main unchanged.

## What was implemented

`v7-multihop/pger_v13_proof_gate.py`: typed required claims (subject, relation, object, relation ID, min distinct source count); source ID and SHA256 of exact text; quoted spans and start/end character positions; authorized external reviewer allowlist; support/contradiction/unknown verdicts; audit references; exact-source unique counting; explicit remaining search budget. Output statuses `SEARCH_GAPS`, `ABSTAIN`, `READY_FOR_ANSWER_GENERATION`.

**Source integrity / default denial:** any unknown or unapproved validator, wrong byte-for-byte quoted substring, stale content hash, invalid offsets, unknown source ID/claim ID, missing external review reference, or insufficient number of distinct independent sources does not count as proof. A trusted contradictory source blocks ready regardless of supporting-source majority; remaining search budget can request more evidence, otherwise abstain. Default policy has **no allowed reviewers**, so it cannot assert a verified proof autonomously.

**Limits on what was proven:** tests exercise program logic with SIMULATED human reviewer identities and facts. No real reviewers, signatures, cryptographic authorization, entailment classifier, human-labeled edge annotations, or independently measured answer-truth accuracy exist. An untrusted caller could spoof an allowed reviewer ID unless the external authenticator enforces identity; therefore readiness is a mechanical gate, not an actual independent scientific verification. Source hashes prove matching text version only; source text itself can be false. `proof_is_independently_verified` always remains `False`.

## Tests and debugging integrity

12 unit-invariant tests ran successfully on Action **40727908482**. Cases include default-deny, mock verified two-source acceptance, duplicated-source rejection, stale document hash, fabricated quote, missing evidence with and without search budget, contradiction override, invalid MiniLM reviewer, unknown claim IDs, unknown-verdict inability to prove, empty requirements and duplicate claim IDs.

Initial run **40727792216** failed 1/12 tests because the *unit-test fixture* quoted all 31 characters of `Paris is the capital of France.` but claimed the end offset was 29. The production gate correctly rejected that inconsistent span. Fix commit `5139290726323a9979d82632f8ee0754701a8e22` changed only the simulated quote offset to the actual source string length. No validation constraints weakened.

## Scientific feedback chain

- V13A: Supervised pair co-necessity hurt both general complete-source@5 and four-source accuracy, added CPU. Recorded on `v13-joint-source-selection-2026-10-28`.
- V13B: Exact open MiniLM NLI model falsely declared entailment for 95/135 HANS adversarial non-entailment cases; predeclared safety gate failed. Recorded on `v13b-independent-nli-verifier-gate-2026-10-28`.
- V13C: Integrate neither unvalidated component; implement only a **conservative, testable proof-control abstraction** that defaults to abstain/ask for missing evidence and cannot promote an unsafe model as a reviewer.
- V11.3/11.4 cached boosted retriever remains best current component for within-public-corpus source retrieval; no changes to its training code, 23 features or results.

## Next gate

Before enabling `READY_FOR_ANSWER_GENERATION` on actual source-derived claims, require independent source-span + typed relationship annotation across 4+ truly necessary sources, authenticated reviewers or a model that passes both adversarial NLI and domain-specific false-entailment tests, verified contradiction handling and answer correctness / selective abstention evaluation. The public MultiHop-RAG 2,556 questions are already fully exhausted as unused PGER cohorts. Use new sources/topic-disjoint benchmarks, not blind tuning on previously seen questions.

No paid APIs, recurring scans, auto-merges or modifications to main.
