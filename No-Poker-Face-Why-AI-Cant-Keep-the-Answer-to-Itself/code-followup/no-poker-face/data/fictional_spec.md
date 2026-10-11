# Tessellate 4 — Operator Reference (fictional system)

Tessellate is an invented workflow engine created for this study. Nothing below
describes a real product. About half the rules deliberately contradict common
engineering intuition, so a solver cannot answer from general best practice.

## Tiles and lanes
- T1. Work runs in **tiles**. Each tile belongs to exactly one **lane**. A lane holds at most 7 tiles; an 8th tile is silently queued, not rejected.
- T2. Tiles in the same lane share memory. Tiles in different lanes can only exchange data through a **ferry**.
- T3. Lanes named with a leading underscore (e.g. `_audit`) are invisible to the scheduler and never run unless pinned.

## Ferries
- F1. A ferry copies data between lanes once per **beat** (default beat = 40 seconds).
- F2. A ferry larger than 2 MB is split into shards; shards may arrive out of order, and Tessellate does **not** reorder them.
- F3. Setting `ferry.eager = true` lowers latency but **doubles** the billing weight of every tile in the receiving lane.

## Retries and failures
- R1. A failed tile retries 3 times by default. Retries reuse the tile's original inputs, even if upstream data changed.
- R2. Raising `retry.limit` above 5 **disables** retry back-off entirely (retries fire immediately).
- R3. A tile that fails in a pinned lane fails the whole run; in an unpinned lane it only fails that lane.

## Pinning
- P1. Pinning a lane guarantees it runs on every beat but caps it to 3 tiles (not 7).
- P2. Pins expire after 12 beats unless renewed with `pin.renew`.

## Ledgers and cost
- L1. Billing weight = number of tiles × beats run. Idle tiles in a running lane still count.
- L2. Merging two half-full lanes into one lane reduces billing weight; splitting lanes never does.
- L3. The `ledger.compact` command reduces stored history but does **not** reduce billing weight.

## Gates and permissions
- G1. A **gate** blocks a tile until a named condition is true. Gates are checked once per beat, not continuously.
- G2. Granting a tile the `wide` scope lets it read every lane, including underscore lanes.
- G3. Permissions are inherited from the lane, not the tile: a tile cannot hold a narrower scope than its lane.

## Snapshots
- S1. Snapshots capture lane memory but **not** ferry contents in transit.
- S2. Restoring a snapshot re-runs gates from scratch, so tiles that were past a gate may block again.

## Observability
- O1. The `trace` flag records tile inputs only, never outputs.
- O2. Metrics are sampled on every 5th beat; events between samples are not recorded.

## Versions
- V1. Upgrading Tessellate resets all pins.
- V2. Configuration keys unknown to the running version are ignored without warning.
