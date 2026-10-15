# gaussian_x3 search benchmark — wave 2 (scored)

Type: research
Target: autofit_inference
Campaign: gaussian-x3-search-benchmark
Epic: search-extensibility (phase B5)
Issue: https://github.com/PyAutoLabs/autofit_inference/issues/8 (B5a); B5b: https://github.com/PyAutoLabs/autofit_inference/issues/10
Filed: 2026-10-14

## Intent

Wave 2 is the **scored** wave of the `gaussian_x3` search benchmark (autofit_inference,
protocol `gaussian_x3@2`,
[`wiki/project/protocol_gaussian_x3.md`](https://github.com/PyAutoLabs/autofit_inference/blob/main/wiki/project/protocol_gaussian_x3.md)
§9 and §11 A2). Within each task (point/MAP, posterior, evidence; never across tasks) it
measures which PyAutoFit searches find the right answer, how reliably across seeds and
data realisations, and the expected wall per right answer. It absorbs the pilot's 297
deferred runs, which are judged under `@2` and never used as calibration input.

## Freeze

`gaussian_x3@2` was frozen in autofit_inference `72d6faaf1717` **before any scored run**.
It was frozen from the existing 17-row wave-1 calibration; the pilot was not restarted.
The 223 pilot rows stay `@1`.

## Menu and identity

The wave runs 50 search seeds × data realisations 1–5 × every non-deferred leg × both
datasets, on `ral_numpy_fp64` and, where the search is JAX-native, `ral_jax_cpu_fp64`.
It runs against a private PyAutoFit checkout pinned at `df6d218f10cd`, the A4 merge.

- The scored arrays are 11 750 runs.
- The probe-first cells (Zeus on JAX, and NSS's 50-step entry) first run a 5-run probe.
  Their timeout comes from that probe, and their remaining 980 runs follow in B5b.
- Warm-started BlackJAXNUTS on the blend is `deferred`: the asserted blend still fails at
  trace time at the pin.

A row belongs to the wave only when its key matches all of
`(dataset, sampler, settings_name, config_id, data_seed, protocol_id, pyautofit_sha)`.
Every expected run is accounted as `row`, `failed`, `missing` or `deferred`
(`scripts/misc/searches/_wave2.py`).

## Submission (2026-10-14, B5a)

All jobs ran on RAL `--partition=ral` only, with job ids on the Cortex ledger
(`autofit_inference` `## Runs`) and in autofit_inference `wiki/project/state.md`:

- references: 408244, 408245
- probe: 408246
- reference builds: 408346, 408347
- scored arrays: 408348, 408365, 408366, 408367, each throttled to `%60`

This task authorizes nothing further: B5a submitted the wave. Nothing has been pulled or
scored yet.

## Pulled and judged (B5b, 2026-10-15, autofit_inference#10)

- **Rows.** All 11,770 rows are admitted under `gaussian_x3@2` at the pin `df6d218f10cd`,
  with none refused (11,750 from the scored arrays and 20 from the probe). The accounting
  (`results/accounting/gaussian_x3_wave2.json`) breaks down as:
  - scored: 10,580 rows and 1,170 failed attempts, with 0 missing and 0 operational
    kills;
  - probe: 20 rows;
  - remainder: 980 missing (submitted);
  - deferred: 250.
- **References.** All 20 per-realisation references are complete. They include only the
  Nautilus runs, because DynestyStatic's ln Z disagrees with Nautilus on every one.
- **Probe timeouts.** The probe-first timeouts, from the probe medians by the frozen
  rule, are 600 s for NSS 50-step and 1168 s for Zeus JAX. Their remaining 980 runs are
  RAL job **409930** on `--partition=ral`.
- **Results.** The results are the `gaussian_x3@2` section of
  `catalogue/search_catalogue.json`: success rate and expected wall per right answer, per
  leg. Legs are ordered within one task and one dataset only.
- **Summary.** `dashboard/summary.json` stays `inference-summary@1`. It carries the
  `protocols` list and the wave-2 accounting, but withholds the wave-2 records: at
  ~84 MB they exceed GitHub's 50 MB warning. That question is open on
  autofit_inference#10.
- **Insight snapshot.** The `fit` snapshot is unchanged in this task. The board's local
  read of the B5b branch (`board --from fit=<checkout>`) ingests it as valid (223 records,
  clean). The receipt and snapshot are refreshed from `main` once autofit_inference PR 1
  merges.

## Next (B5b-2, a separate Mind task)

When 409930 finishes:

1. Pull the remainder and judge the Zeus JAX and NSS cells. This closes the wave.
2. Refresh the `fit` snapshot from `main`.
3. Apply the human's choice of summary form for the wave-2 records.

## Remainder judged; records published (B5b-2, 2026-10-15, autofit_inference#12)

- **Remainder.** RAL job 409930 finished: all 20 array tasks `COMPLETED`, 16:08–17:38
  UTC. Its 980 rows (and the 20 probe rows, byte-identical) were pulled by the B5b tar
  pattern. All 12,750 wave-2 rows are admitted at the pin `df6d218f10cd`, with 0 refused
  and 0 missing, so every leg of the wave is closed (250 blend warm-NUTS runs stay
  deferred).
- **Probe-first legs.** NSS 50-step: 158/250 on the blend and 210/250 on the separated
  control; it leads both evidence rankings. Zeus JAX: 0/250 on the blend and 190/250 on
  the control. The verdicts and ranks are in the `gaussian_x3@2` section of
  `catalogue/search_catalogue.json`; this task only records them.
- **Ordering convention.** The catalogue ranks only legs with a success rate ≥ 50 % over
  ≥ 20 attempts, and lists the rest as unreliable with their numbers. This is a post-hoc
  presentation convention (protocol §8 note), not a verdict.
- **Summary records.** `fit` moves to **`inference-summary@3`**: the index carries
  `record_shards`, and 101 per-protocol, per-leg record files hold the 12,973 records
  (largest 1.6 MB). The ruling said `@2`, but `@2` is already the setups contract
  (`lens`), so the split took the next version. The registry pins `@3` with
  `migrating_from: inference-summary@1`, so the committed `@1` snapshot stays valid
  until the first `@3` capture.
- **Insight snapshot.** It is not refreshed in this task. In a local read of the B5b-2
  branch (`check --from fit=<checkout>`), the `fit` line validates all 12,973 records in
  101 shards. The overall result is still `FAIL`, because any `--from` read changes the
  dashboard input marker; that is expected for a local read.

## Next

1. After autofit_inference#12's PR and this repository's PR merge, the push-triggered
   Dashboard Refresh (or `bin/pyauto-insight board` with a commit) captures `fit` under
   `@3` from `main`. Then run `bin/pyauto-insight check` online and drop `migrating_from`.
2. B5c, a second model family.
