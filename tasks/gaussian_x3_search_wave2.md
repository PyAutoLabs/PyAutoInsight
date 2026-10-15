# gaussian_x3 search benchmark — wave 2 (scored)

Type: research
Target: autofit_inference
Campaign: gaussian-x3-search-benchmark
Epic: search-extensibility (phase B5)
Issue: https://github.com/PyAutoLabs/autofit_inference/issues/8
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

## Next (B5b, a separate Mind task)

When the arrays finish:

1. Pull the results.
2. Build the JAX blend realisation-1 reference on the laptop. Any re-judging of the
   pilot's `@1` rows against it is a reassessment and must be decided explicitly.
3. Set the probe-first timeouts and submit the rest of those cells.
4. Judge every row under `@2`, catalogue it, and publish the wave-2 summary.
5. Refresh the Insight `fit` snapshot only then.
