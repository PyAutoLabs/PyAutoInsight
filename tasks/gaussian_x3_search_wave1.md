# gaussian_x3 search benchmark — wave 1 (the pilot)

Type: research
Target: autofit_inference
Campaign: gaussian-x3-search-benchmark
Epic: search-extensibility (phase B3)
Issue: https://github.com/PyAutoLabs/autofit_inference/issues/4
Filed: 2026-10-08

## Intent

Wave 1 is the **exploratory pilot** of the `gaussian_x3` search benchmark
(autofit_inference, protocol `gaussian_x3@1`,
[`wiki/project/protocol_gaussian_x3.md`](https://github.com/PyAutoLabs/autofit_inference/blob/main/wiki/project/protocol_gaussian_x3.md)).
It **ranks nothing**. It exists to:

1. run every registered PyAutoFit search once per seed on the toy problem, so the
   catalogue (`catalogue/search_catalogue.json`) can give every search a status —
   measured, unsupported, deferred or failed — grouped by the task it answers
   (point/MAP, posterior, evidence), never compared across tasks;
2. calibrate the protocol's PLACEHOLDER thresholds (σ-ratio band, ppc tolerance, mode
   radius, ESS and R-hat bars), the per-search timeouts and the censoring rule on the
   reference runs' seed scatter and the pilot (decision D16 iii), and freeze them as
   `gaussian_x3@2` before any wave-2 row.

## Menu (protocol §1, §9)

10 search seeds × both datasets (`gaussian_x3_blend`, the `gaussian_x3_separated`
disjoint-prior control) × `local_numpy_fp64`, and `local_jax_cpu_fp64` where the search
is JAX-native, on PyAutoFit `main` (post-A1), every row flagged `pilot` and stamped with
its PyAutoFit commit:

- point/MAP: LBFGS, BFGS, MultiStartAdam, MultiStartProdigy, MultiStartADABelief,
  MultiStartLion;
- posterior: Emcee, Zeus (numpy and JAX legs), BlackJAXNUTS cold and warm from a short
  Nautilus, SMC;
- evidence: Nautilus (`n_live` 100/200/400), DynestyStatic, DynestyDynamic; NSS is
  `deferred` until phase A3b (NSS onto Fitness);
- Drawer is a sanity floor and is not benchmarked (`unsupported` in the catalogue).

The expected-run manifest is `scripts/misc/searches/_pilot.py`; every expected run with
no row is published as deferred with its reason (`coverage.expected` of the summary), so
a missing run is never silently absent.

## Where things live

- **Execution and rows**: autofit_inference (`results/searches/`, the exporter's
  `dashboard/summary.json`, instance `fit` in this registry).
- **Science record**: PyAutoCortex row `autofit_inference` (ledger
  `wiki/project/state.md` in the project repo).
- **Verdict commentary**: autofit_inference `wiki/project/state.md` (journal entry
  2026-10-08). The planned autofit_assistant campaign page is not made in B3:
  autofit_assistant gitignores dated `wiki/project/` entries (they are per-clone memory,
  never shipped with the template), so its home needs a human decision.
- **Bounded implementation work**: PyAutoMind (the search-extensibility epic).

## Boundaries

Local CPU only. Wave 2 (scored: 50 seeds × 5 data realisations) runs on RAL
`--partition=ral` only — never `gpu`, `ral,gpu` or `gpu,ral` — on a PyAutoFit revision
frozen after phases A2 and A4 (phase B5). This task authorizes no compute submission.

## Status at the B3 wrap-up (2026-10-08)

The pilot was stopped by the human wrap-up ruling with **223 of 520** expected runs on
disk (autofit_inference#4). It ranks nothing. Every run without a row is published as
`deferred` with its reason: wave 2 on RAL `--partition=ral`, NSS to phase A3b. The
pilot ran on PyAutoFit main `0dbf258c4f5e`, before phase A2 (PyAutoFit#1679, gradients
under JAX); BFGS/LBFGS non-finite results are expected to change once A2 merges and are
not a judgement on those searches. The JAX blend reference is pending (2 of 3 Nautilus
runs), so JAX blend rows are `not_assessed`. The calibration record keeps `@1` (17
calibration rows < 20); the `gaussian_x3@2` freeze is deferred and still precedes any
wave-2 row.
