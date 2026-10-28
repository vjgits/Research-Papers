# PGER V13A: learned source-pair co-necessity DOES NOT verify a proof chain — negative

**Date:** October 28, 2026.
**Successful GitHub Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40727022041
**Full per-question artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40727022041/artifacts/12833635887
**Branch:** v13-joint-source-selection-2026-10-28. Main unchanged.

## Method and integrity
Unchanged MultiHop-RAG 609 public news source corpus (ODC-BY) and original PGER V11.4 fixed BM25/V7.1 + two facets, cached 23-feature boosted necessity scorer, at most 120 candidate source articles. Trained on 316 development questions at fixed indices 0..399; the new **pair co-necessity** classifier learns if *both* candidate sources were annotated gold for a question, using 710 positive and 28,440 negative training source-pairs, twelve similarity/relevance/overlap features and a regularized LogisticRegression. **It does NOT learn verified directional factual relations, source-to-source entailment, negation, or source necessity under counterfactual removal.**

Test was the **last untouched** original MultiHop-RAG question slice 2400..2555: 156 public questions, 126 had unambiguous gold source identity, 30 excluded. Although question IDs were previously unused by PGER, all questions share the SAME 609 source documents; some topics may leak. Of the 126 evaluated test questions, only 14 had all gold source identities unseen among training gold sources, so true source-disjoint generalization cannot be concluded. Gold annotations enter *only post-ranking* for test cases.

## Complete annotated article identities @5 and @10

| Arm | Overall AE@5 | AE@10 | Two gold sources (n=58) | Three (n=46) | Four (n=22) |
|---|---:|---:|---:|---:|---:|
| BM25 | 42.0635% | 65.8730% | 41 | 11 | 1 |
| V7.1 fast | 41.2698% | 65.8730% | 41 | 10 | 1 |
| **PGER boosted standalone** | **57.9365%** | 76.9841% | **51** | **16** | **6** |
| Nonlearned text diversity | 58.7302% | 76.9841% | 51 | 17 | 6 |
| Learned co-necessity weak weight .11 | 53.9683% | 75.3968% | 51 | 14 | 3 |
| Learned co-necessity strong weight .23 | 50.7937% | 75.3968% | 47 | 14 | 3 |

Strong pair arm minus unchanged PGER boosted: **-7.143 pp**, paired question bootstrap 95% interval **[-12.698,-1.587]**, 2 wins, 11 losses. Weak pair arm -3.968 pp, interval [-8.730,0], 1 win, 6 losses. Simple diversity vs PGER +0.794 pp, interval [0,+2.381], only one additional success and no meaningful evidence of improvement. 

**High-value negative:** ALL 22 four-source questions had all four gold sources in the **top 56** original boosted candidate order, but PGER Top5 recovered 6 and pair selectors only 3. A relational or set-selection method cannot be justified by a score trained solely on independently labeled *co-occurrence of gold sources* when it makes the critical four-source outcome worse. Do not promote. If re-exploring this avenue, need explicit annotated source-to-source logical relations, conflict and necessity labels, and a credible set-level objective.

## CPU
Mean additive post-index process CPU per scored question: initial 1.503 ms; extra facet searches 1.742 ms; cached features 3.145 ms; boosted prediction 1.010 ms. Pair inference and feature generation added **21.308 ms**; listwise weak/strong selection ~4.07/4.03 ms on top. Thus ~32.8 ms vs PGER boosted ~7.4 ms; no accuracy/compute gain. The nonlearned diversity control also took ~17.3ms and added only 1 correct question; reject as efficiency improvement.

## Decision
Record V13A failure, keep PGER boosted as experimental leading component. A score predicting both docs were labeled relevant is **NOT** entailment or source-necessity proof. Existing literature on listwise ranking and pairwise ranking is prior art; novelty not established.

Next locked V13B independently audits an Apache-2.0 NLI classifier on **HANS** adversarial entailment labels, including false-acceptance under word-overlap heuristics. Even if it passes HANS, a real PGER proof/verifier needs individually annotated source spans + typed relation/direction + contradiction/unknown labels. Do not integrate into retrieval or claim answer truth before a relevant domain-specific blinded audit. Other remaining steps: source-disjoint held-out corpus; same-budget official comparator implementations; 4/5/6/8+ genuine logical hop tests with TopK feasibility.

No API spending, background scans, merges, model hot-swap, or main-branch writes.
