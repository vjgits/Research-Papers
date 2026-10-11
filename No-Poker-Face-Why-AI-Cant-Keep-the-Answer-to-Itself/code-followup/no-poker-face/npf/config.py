"""Study configuration: models, prices, conditions, phase sizes.

Prices are USD per million tokens (input, output), standard tier, taken from the
providers' pricing pages on 2026-10-05/06. Batch API halves both. Re-check before
each run; rates are timestamps.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RUNS = ROOT / "runs"

PRICES = {
    # Anthropic
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    # OpenAI
    "gpt-5.6-sol": (5.00, 30.00),
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-luna": (0.20, 1.20),
    # Google (ai.google.dev/gemini-api/docs/pricing, read 2026-10-06; thinking billed as output).
    # gemini-3.6-flash and 3.8-flash are $0.75/$3.75 through 2026-12-31, then $1.50/$7.50.
    # 3.6-flash is the strong Gemini solver: it accepts thinkingLevel "minimal" (0 thinking tokens, verified 2026-10-06);
    # 3.8-flash does not (lowest "low" = 270-980 thinking tokens per item) and is kept here only for the smoke-test ledger.
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.00, 12.00),   # Gemini writer arm (addendum); prompts <= 200k tokens
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.7-flash": (0.75, 3.75),
}

PROVIDER = {m: ("anthropic" if m.startswith("claude") else "google" if m.startswith("gemini") else "openai") for m in PRICES}
FAMILY = {m: PROVIDER[m] for m in PRICES}

# Writers: one frontier model per family, run at provider defaults (out-of-box behaviour).
WRITERS = ["claude-opus-5-5", "gpt-5.6-sol"]

# Solvers never come from the writer's family: a small and a strong model per family.
SOLVERS = {
    "anthropic": ["claude-haiku-4-5-20251001", "claude-sonnet-5-5"],
    "openai": ["gpt-5.6-luna", "gpt-5.6-terra"],
    "google": ["gemini-3.1-flash-lite", "gemini-3.6-flash"],   # third family (added 2026-10-06): solver and panel only
}

# Gemini is cross-family for both writers, so every item is also solved by it (decided 2026-10-06).
EXTRA_SOLVER_FAMILIES = ["google"]


# Gemini writer arm (addendum, 2026-10-07): a third writer family. Its items are solved, probed and judged only by
# Anthropic and OpenAI models; it is not part of the registered main run (which uses the frozen code at a53ed95).
GEMINI_WRITER = "gemini-3.1-pro-preview"


def other_family(writer):
    """The family that supplies the simulated learner. For the Gemini writer: OpenAI (gpt-5.6-luna)."""
    if FAMILY[writer] == "google":
        return "openai"
    return "openai" if FAMILY[writer] == "anthropic" else "anthropic"


def cross_solvers(writer):
    """Solvers allowed for a writer's items: never the writer's own family."""
    if FAMILY[writer] == "google":
        return SOLVERS["anthropic"] + SOLVERS["openai"]
    return SOLVERS[other_family(writer)] + [m for f in EXTRA_SOLVER_FAMILIES for m in SOLVERS[f]]

# Judges code every item blind to condition and writer: one per family.
JUDGES = ["claude-sonnet-5-5", "gpt-5.6-terra"]

# Generation settings
WRITER_MAX_OUT = 16000          # cap includes any reasoning tokens
SOLVER_MAX_OUT = 32             # letter only; reasoning disabled where the API allows
SOLVER_REASONING = "none"       # OpenAI reasoning effort for solvers (fallback handled in client)
JUDGE_MAX_OUT = 2500
SLOTS_PER_CALL = 10             # writer receives the blueprint in sets of 10 slots

# Conditions. 'guide' cells add item-writing guidelines; they are length-matched to each
# other, the six non-guideline cells are length-matched to each other.
CONDITIONS = {
    "N":  {"label": "Neutral",                  "parts": [],                       "guide": False},
    "G":  {"label": "Goal",                     "parts": ["goal"],                 "guide": False},
    "W":  {"label": "Weak areas",               "parts": ["weak"],                 "guide": False},
    "WH": {"label": "Weak areas + hard",        "parts": ["weak", "hard"],         "guide": False},
    "WE": {"label": "Weak areas + emotion",     "parts": ["weak", "emotion"],      "guide": False},
    "R":  {"label": "Weak areas + error notes", "parts": ["weak", "notes"],        "guide": False},
    "NG": {"label": "Neutral + guidelines",     "parts": [],                       "guide": True},
    "WG": {"label": "Weak areas + guidelines",  "parts": ["weak"],                 "guide": True},
}
PRIMARY_CONTRAST = ("N", "W")

SOLVE_MODES = ["full", "options_only", "mismatched"]

PHASES = {
    # 40 slots (20 real + 20 fictional) x 8 conditions x 2 writers x 1 sample
    "smoke":       {"domains": ["real", "fictional"], "slots_per_domain": 10, "conditions": ["N", "W"], "samples": 1},
    "calibration": {"domains": ["real", "fictional"], "slots_per_domain": 20, "conditions": list(CONDITIONS), "samples": 1},
    # Part B pilot: 2 invented subjects x 2 writers x 3 session types (C, F, FT) x 1 = 12 sessions
    "pilot_sessions": {"subjects": ["tessellate", "corvane"], "reps": 1, "judge_share": 0.3,
                       "domains": [], "slots_per_domain": 0, "conditions": [], "samples": 0},
    # Part B v2 (expanded design, handoff v4 §4b). Pilot of the new types on the two new subjects (16 sessions),
    # then the pre-registered main run (4 subjects x 2 writers x 7 types x 3 reps = 168 sessions).
    "pilot_sessions_v2": {"design": "v2", "subjects": ["tarnball", "llmapi"], "stypes": ["IMP", "CLAIM", "FAIL-LO", "FAIL-HI"],
                          "reps": 1, "judge_share": 0.3, "domains": [], "slots_per_domain": 0, "conditions": [], "samples": 0},
    # Gemini writer arm (addendum). Pilot: 4 sessions on Tarnball; arm: same 84-session layout as one writer of the main run.
    "gemini_arm_pilot": {"design": "v2", "writers": ["gemini-3.1-pro-preview"], "subjects": ["tarnball"],
                         "stypes": ["C", "FT", "CLAIM", "FAIL-HI"], "reps": 1, "judge_share": 0.3, "wave_high": 8.0,
                         "domains": [], "slots_per_domain": 0, "conditions": [], "samples": 0},
    "gemini_arm": {"design": "v2", "writers": ["gemini-3.1-pro-preview"], "subjects": ["tessellate", "corvane", "tarnball", "llmapi"],
                   "stypes": ["C", "F", "FT", "IMP", "CLAIM", "FAIL-LO", "FAIL-HI"], "reps": 1, "judge_share": 0.3,
                   "wave_high": 57.4, "domains": [], "slots_per_domain": 0, "conditions": [], "samples": 0},  # 28 sessions x $1.64 (mini-pilot) x 1.25; author decision 2026-10-07: 1 rep, cap $60
    "main_sessions": {"design": "v2", "subjects": ["tessellate", "corvane", "tarnball", "llmapi"],
                      "stypes": ["C", "F", "FT", "IMP", "CLAIM", "FAIL-LO", "FAIL-HI"],
                      "reps": 3, "judge_share": 0.3, "domains": [], "slots_per_domain": 0, "conditions": [], "samples": 0},
    # Main study size is set by simulate_power() from calibration output; this is a placeholder.
    "main":        {"domains": ["real", "fictional"], "slots_per_domain": 20, "conditions": list(CONDITIONS), "samples": 5},
}
