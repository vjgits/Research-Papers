"""Deterministic item features: no model involved, so these are exactly reproducible."""
import re

STOP = set("""a an the and or of to in on for with by at from as is are was were be been being it its this that these those
which who whom what when where why how than then so such not no nor but if into out over under about after before
can could should would will may might must do does did done has have had having you your yours we our they their them
he she his her i me my one two three four any all each every some more most less least very only just also there here
use used using uses""".split())


def words(s):
    return re.findall(r"[a-z][a-z0-9_'-]*", s.lower())


def content(s):
    return [w for w in words(s) if w not in STOP and len(w) > 2]


def bigrams(ws):
    return set(zip(ws, ws[1:]))


def item_features(it, notes):
    opts, key = it["options"], it["answer"]
    lens = {k: len(v.split()) for k, v in opts.items()}
    others = [lens[k] for k in opts if k != key]
    longest = lens[key] > max(others)
    longest_or_tied = lens[key] >= max(others)
    mean_o = sum(others) / 3
    stem_c = set(content(it["stem"]))
    key_c = set(content(opts[key]))
    wrong_c = set().union(*[set(content(opts[k])) for k in opts if k != key])
    key_only_overlap = sorted((stem_c & key_c) - wrong_c)
    wrong_only = [sorted((stem_c & set(content(opts[k]))) - key_c) for k in opts if k != key]
    # near-duplicate options: any pair with Jaccard >= 0.7 on content words
    sets = {k: set(content(v)) for k, v in opts.items()}
    ks = list(opts)
    jac = [len(sets[a] & sets[b]) / max(1, len(sets[a] | sets[b])) for i, a in enumerate(ks) for b in ks[i + 1:]]
    # rule-echo overlap: computed in every condition against the same notes, so W and N give the baseline for R
    stem_key_w = content(it["stem"] + " " + opts[key])
    sk_bi = bigrams(stem_key_w)
    best_bi, best_j = 0, 0.0
    for n in notes:
        nw = content(n)
        best_bi = max(best_bi, len(sk_bi & bigrams(nw)))
        best_j = max(best_j, len(set(stem_key_w) & set(nw)) / max(1, len(set(nw))))
    return {
        "key_len": lens[key], "key_len_ratio": lens[key] / max(1e-9, mean_o), "key_longest": longest,
        "key_longest_or_tied": longest_or_tied, "stem_len": len(it["stem"].split()),
        "stem_key_only_overlap_n": len(key_only_overlap), "stem_key_only_overlap": key_only_overlap,
        "stem_wrong_only_overlap_n": max(len(w) for w in wrong_only),
        "near_duplicate_options": max(jac) >= 0.7, "max_option_jaccard": max(jac),
        "notes_bigram_overlap": best_bi, "notes_word_coverage": best_j,
    }
