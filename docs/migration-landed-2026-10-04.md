# Inference task migration — landed 4 October 2026

This implementation record is not a scientific check-in. The campaign ledger
retains `last_checkin: null`; no compute was submitted or scientific acceptance,
threshold or campaign approval changed.

## Destination before source removal

[Insight PR #2](https://github.com/PyAutoLabs/PyAutoInsight/pull/2) merged at
`aabc4869410824a62cf1816925cda7f88994b95a` before source deletion. Cleanup verified
that commit was on Insight main, then read each destination from that commit
and checked its SHA256 against the exact original.

[Mind PR #472](https://github.com/PyAutoLabs/PyAutoMind/pull/472) subsequently
merged at `9aeabfe99b1e511a0d48ca6a9db415ced117c654`. It removed five original
prompts (prior centering, Cortex documentation, EP campaign, EP scoping and
graphical scoping) plus the original NUTS/HMC trial idea line. All six originals
remain byte-preserved under `tasks/`; `migration.yaml` maps exact source paths,
source revision and hashes. Current Mind epic/idea references now point here,
and its dashboard was regenerated. Mind retains bounded implementation work,
claims and history. Cortex retains scientific run records and human conclusions.

Prior centering remains blocked on release verification. EP work retains
slicing/decision gates; the sampler trial remains an unapproved idea. Only the
Cortex-documentation task is marked complete, backed by
[producer PR #18](https://github.com/PyAutoLabs/autolens_inference/pull/18), merged
at `26778b158538711a5a79acbadb0699a103446bd7`. Its original text is unchanged.

## Producer refresh evidence

[Producer publication run 37187664457](https://github.com/PyAutoLabs/autolens_inference/actions/runs/37187664457)
succeeded and dispatched
[Insight receiver run 37187697228](https://github.com/PyAutoLabs/PyAutoInsight/actions/runs/37187697228).
The successful receiver payload source `26778b158538711a5a79acbadb0699a103446bd7`
matches `receipts/lens.json`: outcome `ok`, captured `2026-10-04T08:09:22Z`,
56 records, no cached fallback. Receiver evidence landed on Insight main
`e226beaa58fe8334a52f08a6c97da6f86e7e2551`; this update retains that receipt.

These are publication/ingestion facts, not evidence of current cluster jobs.
Unknown measurement timestamps, sample/archive access and qualification remain
unknown. Eight tracked campaigns do not imply eight running jobs or producers:
autolens_inference is the sole real feed; the second producer is a test fixture.

## Validation

Mind cleanup passed 619 tests, lifecycle/index checks, registry contents and
generated-dashboard freshness. Insight passes its 77 tests, Ruff, migration
hash validation and offline ledger/receipt/dashboard checks. A genuine campaign
sweep remains a separate operation under `CHECKIN.md`; this record does not
substitute for one.
