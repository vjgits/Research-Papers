# Boundary Contamination in LLM Workflows

Asking a model to check its work can improve the answer and still make the returned
response unusable. The model corrects the figure, then wraps the corrected answer in
commentary the task forbade. This paper measures that separately from whether the
deliverable itself is correct, and audits the instrument used to measure it.

**Paper** · [10.5281/zenodo.22735762](https://doi.org/10.5281/zenodo.22735762) — v1.46, preprint
**Evidence archive** · [10.5281/zenodo.22738017](https://doi.org/10.5281/zenodo.22738017) — dataset, 17.5 MB
**All versions** · [10.5281/zenodo.20271843](https://doi.org/10.5281/zenodo.20271843) — concept DOI, always resolves to the latest

## What the paper reports

Three experiments: a 576-response product study, a 360-response direct-API factorial, and
a held-out probe bank of 300 responses written after the scorer was frozen.

On the held-out bank, checking-only instructions produced boundary contamination in 14 of
30 responses for one model and 0 of 30 for another under an identical prompt. A single
clause restating the output format suppressed it in 14 of 14 paired cases, none in the
reverse direction. Deliverable quality was unchanged; only the compliance of the response
containing it moved.

The paper also audits its own measuring instrument. Of 34 recorded failures, 22 were
defects in the checker rather than in the responses, across five defect classes, and one
claimed finding was withdrawn after re-measurement. Two independent raters adjudicated 47
masked cases against the automated boundary measure and agreed with it on every real case
they rated, while disagreeing with it in the same three places on constructed probes that
expose a disclosed detection limit.

Results come from fixed constructed banks and do not estimate ordinary-use error rates.
The contamination effect is conditional on the model and configuration tested. It is not a
general property of LLM workflows and not a vendor ranking.

## What is in this folder

| File | |
|---|---|
| [`paper/v1.46/Boundary_Contamination_v1_46.pdf`](paper/v1.46/Boundary_Contamination_v1_46.pdf) | The paper, 48 pages |
| [`paper/v1.46/CHANGE_LOG_v146.txt`](paper/v1.46/CHANGE_LOG_v146.txt) | Every change from the previously published version |
| [`paper/v1.46/README_Supplementary_Evidence.md`](paper/v1.46/README_Supplementary_Evidence.md) | Guide to the evidence archive: what is in it, how to verify it, what to run and what not to run |
| [`paper/v1.46/SHA256SUMS.txt`](paper/v1.46/SHA256SUMS.txt) | Checksums for the paper, the archive, and the archive's guide |

The evidence archive itself is not in this repository. It lives on Zenodo under the DOI
above, where it is citable and permanently archived. Downloading it here would give you a
second copy with no authority over the first.

## Verifying the archive

Download the ZIP from the Zenodo dataset record, put it beside `SHA256SUMS.txt`, and:

    sha256sum -c SHA256SUMS.txt

Then, inside the extracted archive, every file is listed with its hash:

    python3 - <<'EOF'
    import json, hashlib
    from pathlib import Path
    m = json.load(open('MANIFEST_SHA256.json'))
    bad = [k for k, v in m.items()
           if hashlib.sha256(Path(k).read_bytes()).hexdigest() != v]
    print('files checked:', len(m), ' mismatches:', len(bad))
    EOF

3,327 files are covered. `MANIFEST_SHA256.json` is the only unlisted file, because it
cannot contain its own hash.

For Study H specifically, the sealed answer key matches the SHA-256 committed in
`StudyH_v2_MANIFEST_SHA256.txt` before any rating began, so that sealing is verifiable
without trusting the author.

File verification establishes preservation. It does not establish that the measuring
instrument is correct — which is the point of the instrument audit in the paper.

## Earlier versions

This paper was previously titled *Observed Recoverable Behavioral Failures in LLM Workflows*.
All material from that lineage — the v1.23 and v1.33 manuscripts, the experiment pack, the
research archive and the earlier tooling — is preserved unchanged at
[`archive/Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/`](../archive/Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/).

- **v1.33 · September 2026** — superseded by v1.46; no result, count, table or figure changed between them
- **v1.23 · May 2026** — [doi:10.5281/zenodo.20271844](https://doi.org/10.5281/zenodo.20271844)

The Zenodo lineage is continuous: the concept DOI above resolves to the latest version
regardless of title.

## Citing

    Suresh, V. (2026). Boundary Contamination in LLM Workflows (Version 1.46) [Preprint].
    Zenodo. https://doi.org/10.5281/zenodo.22735762

To cite the evidence separately, use the dataset DOI. To cite the work irrespective of
version, use the concept DOI.

## Licence

The paper and the evidence archive are released under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). You may reuse, adapt and build
on them, including commercially, provided you give attribution.

## Author

Vijay Suresh · Independent Researcher · [ORCID 0009-0004-1471-0561](https://orcid.org/0009-0004-1471-0561)
