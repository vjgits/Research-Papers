# Boundary Contamination in LLM Workflows
## Supplementary evidence for the manuscript

This guide accompanies `Boundary_Contamination_v1_45_Supplementary_Evidence.zip`, the research
supplement for the manuscript deposited in the companion Zenodo record. The two are deposited as
separate records and linked to each other: the manuscript record is the citable paper, this one
is the evidence.

The ZIP filename retains `v1_45` because that is the manuscript version it was assembled against
and the archive is hash-sealed under that name. It is the evidence for the manuscript as
deposited (v1.46). Between v1.45 and v1.46 the abstract was rewritten, one Study 1 subsection and
the evidence-provenance section were relocated to appendices, section numbering after §9 shifted,
and the document was reformatted. No result, count, table, figure or statistic changed. The
manuscript's own change log records every edit.

## Contents and scope

The ZIP is a curated research supplement, not the editorial revision package. Editorial ratings,
open-question documents and manuscript builders are excluded. Research packets and study
artifacts remain included, even when their format is PDF or Word — this includes five earlier
manuscript `.docx` files preserved inside `Earlier_Studies_v1_38/Historical_and_prospective/`,
which are part of that archive's byte-for-byte copy. Source evidence is copied byte-for-byte. A
provenance inventory and SHA-256 manifest are inside the ZIP.

`Earlier_Studies_v1_38/` contains the public Study 1 and Study 2 data, code, artifacts, and
historical/prospective evidence from the v1.38 research archive. Its README and prospective status
describe that historical release, not the status of the completed later experiments.

`Direct_API_and_Audit_v1_40/` contains the completed 360-response direct-API factorial, collection
provenance, and the unblinded scoring sensitivity audit. Its unscored independent review packet and
commitment are included; the private mapping is not. This is separate from completed Study H.

`D02_StudyH_and_Locks/` contains the held-out D02 instrument, requests, raw outputs, frozen and
corrected scores, render-check record, completed Study H packets, de-identified rater sheets,
released machine key and analyzer, and numerical locks and corrections. The earlier unrated Study H
packet is historical. The completed packet is `evidence/StudyH_v2/`. The current cumulative
numerical authority is `13_NUMBERS_LOCK_CONSOLIDATED_studyh.json`. The author's rater-independence
confirmation is recorded in `Disclosure_Amendment.json`; prior placeholder notes are superseded.
Human validation remains limited to the boundary measure, as stated in the manuscript.

## Verification

    sha256sum -c SHA256SUMS.txt          # this guide and the ZIP
    # then, inside the extracted ZIP:
    python3 - <<'EOF'
    import json,hashlib
    from pathlib import Path
    m=json.load(open('MANIFEST_SHA256.json'))
    bad=[k for k,v in m.items() if hashlib.sha256(Path(k).read_bytes()).hexdigest()!=v]
    print('files checked:',len(m),' mismatches:',len(bad))
    EOF

The archive carries 3,327 files under `MANIFEST_SHA256.json`; the manifest itself is the only
unlisted file, since it cannot contain its own hash. `SOURCE_INVENTORY.json` records each copied
file's origin and hash. File verification establishes preservation, not independent correctness of
the measuring instrument or of historical timestamps.

For Study H, the sealed key `StudyH_v2_KEY.json` matches the SHA-256 committed in
`StudyH_v2_MANIFEST_SHA256.txt` before rating began, so the sealing is independently checkable.
The key is released; anyone re-running the packet with new raters should regenerate it.

## Reproduction entry points

Read the study-specific READMEs before running code. From `Direct_API_and_Audit_v1_40/`, the
preserved README identifies freeze verification, scorer tests, collection auditing and
`Scoring_sensitivity/audit_sensitivity.py`. These operate on saved data. Do not run collection
runners merely to inspect or reproduce existing scores; they make new paid provider calls.

For completed Study H, from `D02_StudyH_and_Locks/evidence/StudyH_v2/`:

    python3 StudyH_v2_analyze.py StudyH_v2_scoring_sheet_RATER1_filled.csv StudyH_v2_scoring_sheet_RATER2_filled.csv

The original analyzer and its post-rating synonym normalization are preserved as disclosed. H11
remains in calculations and is excluded only from substantive probe interpretation. Original
intervals and other locked statistics have not been recomputed for this packaging step.

Original freeze manifests apply to their original paths and scopes.

## Deposit

The manuscript and this supplement are deposited as two linked Zenodo records. The manuscript
record carries the title *Boundary Contamination in LLM Workflows* and is the record to cite. This
supplement is deposited as a separate Dataset record, related to the manuscript record by
`is supplement to`, with the manuscript record carrying the reciprocal `is supplemented by`.
Citing the manuscript DOI reaches the paper; the supplement appears as a linked related identifier
rather than as an alternative version of the paper.
