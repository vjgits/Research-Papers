"""Secondary arms vs the same writer's original W items on the same slots."""
import json
import pandas as pd
from .analysis import collapse_codes
from .features import content
from .pipeline import read_jsonl


def run(outdir):
    base = pd.DataFrame(read_jsonl(outdir / "items.jsonl"))
    base = base[(base.cond == "W") & (base["sample"] == 0)]
    sec = pd.DataFrame(read_jsonl(outdir / "secondary_items.jsonl"))
    rows = []
    for name, items, d in [("W_original", base, outdir), ("arms", sec, outdir / "secondary")]:
        sol = pd.DataFrame(read_jsonl(d / "solves.jsonl"))
        sol = sol[sol.id.isin(items.id)]
        acc = sol[sol.parsed].pivot_table(index="id", columns="mode", values="correct", aggfunc="mean")
        feats = pd.DataFrame(read_jsonl(d / "features.jsonl")).set_index("id")
        cc, _ = collapse_codes(pd.DataFrame(read_jsonl(d / "codes.jsonl")))
        t = items.set_index("id").join(acc).join(feats[["key_longest", "notes_bigram_overlap"]]).join(cc.set_index("id"))
        t["arm"] = t.get("arm", pd.Series("W_original", index=t.index)).fillna("W_original")
        rows.append(t.reset_index())
    t = pd.concat(rows)
    slots = set(sec.writer + sec.domain + sec.slot)
    t = t[(t.writer + t.domain + t.slot).isin(slots)]
    # novelty: max content-word Jaccard of each new stem against every original stem from the same writer/domain
    orig = {(r.writer, r.domain): [set(content(s)) for s in base[(base.writer == r.writer) & (base.domain == r.domain)].stem]
            for r in sec.itertuples()}
    def maxsim(r):
        s = set(content(r.stem))
        return max(len(s & o) / max(1, len(s | o)) for o in orig[(r.writer, r.domain)])
    t["max_stem_jaccard_to_W"] = t.apply(maxsim, axis=1)
    summ = t.groupby(["arm", "domain"]).agg(n=("id", "size"), options_only=("options_only", "mean"), full=("full", "mean"),
                                           mismatched=("mismatched", "mean"), key_longest=("key_longest", "mean"),
                                           deciding_fact_both=("deciding_fact_in_stem_both", "mean"),
                                           max_sim_to_W=("max_stem_jaccard_to_W", "mean")).round(3)
    near = t[t.arm == "novelty"].assign(near_repeat=lambda z: z.max_stem_jaccard_to_W >= 0.5)
    audit = sec[sec.arm == "audit"]
    n_changes = audit.groupby(["writer", "domain"]).changes.first().apply(lambda c: len(c) if isinstance(c, list) else 0)
    return t, summ, near, n_changes
