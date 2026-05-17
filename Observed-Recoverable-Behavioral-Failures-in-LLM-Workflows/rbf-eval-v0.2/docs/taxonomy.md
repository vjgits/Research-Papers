# RBF-Eval Taxonomy

RBF-Eval uses the following failure-mode codes:

- PTS: Premature Termination of Search
- BDTF: Breadth-Depth Tradeoff Failure
- SMI: Search Methodology Inconsistency
- MRT: Mid-Response Truncation
- MSI: Mobile Streaming Interruption
- FPG: Feedback Persistence Gap
- RFI: Retry-Failure Invisibility
- STK: Stale Third-Party Tool/UI Knowledge
- QI: Quantitative Inconsistency
- PPG: Phantom Placeholder Persistence
- UCT: Usage-Cap Termination
- VMC: Visual Misreading Cascade
- AFF: Artifact Finalization Failure
- SVD: Source Verification Drift
- EBC: Editorial Boundary Contamination
- ACM: Audience / Context Miscalibration

Mode assignments should be conservative. If retry success requires new substantive information from the user, the event is not counted as an RBF.
