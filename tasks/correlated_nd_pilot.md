# correlated_nd search benchmark — the pilot (wave 1)

Type: research
Target: autofit_inference
Campaign: gaussian-x3-search-benchmark
Epic: search-extensibility (phase B5c)
Issue: https://github.com/PyAutoLabs/autofit_inference/issues/14
Filed: 2026-10-15

## Intent

The second toy-likelihood family of the PyAutoFit search benchmark, so rankings stop
resting on `gaussian_x3` alone. `correlated_nd` stresses scaling with dimension and
adaptation to an ill-conditioned, correlated or curved posterior. It has correlated
Gaussians at D = 20, 50 and 100, each with condition number 10³, and a D = 20 hybrid
Rosenbrock banana. Their posteriors and ln Z are **exact by construction**.

The rows are judged by the family's own pre-registered protocol `correlated_nd@1`
([`wiki/project/protocol_correlated_nd.md`](https://github.com/PyAutoLabs/autofit_inference/blob/main/wiki/project/protocol_correlated_nd.md)).
It was first committed as autofit_inference `9ec37795f404`, before any row, and amended
by A1 before any row or submission. The catalogue groups this family by task and
dataset, in its own `correlated_nd@1` section, separately from `gaussian_x3`. **Nothing
is ranked across families**, and the pilot ranks nothing at all.

## Menu and identity

The menu is the `gaussian_x3` wave-2 search menu, unchanged. It runs 10 search seeds
(0–9) × realisation 1 × every non-deferred cell × the four datasets.

- **Planned: 930 runs.** The family expects 1040 runs in all.
- **Deferred: 110 runs, each with its reason** (protocol §7):
  - Emcee and Zeus at D ≥ 50: their 50 walkers are fewer than 2D, so both samplers
    refuse to run.
  - DynestyStatic `nlive_200` and NSS at D = 100: `n_live` is below the exact
    information H = 267.6 nat.

The runs go on RAL `--partition=ral` against the private PyAutoFit pin `df6d218f10cd`.
Each run has a 4 h operational process cap. A capped run is a censored failure, not a
protocol timeout.

A row belongs to the pilot only when its key
`(dataset, sampler, settings_name, config_id, data_seed, protocol_id, pyautofit_sha)` is a
cell of the pilot, and its `model` is `correlated_nd`
(`scripts/misc/searches/_correlated_nd.py`).

## References

Every dataset × backend has an exact reference, complete in `results/reference/` (8 of
8). Each one passed the §6 agreement test:

- the backend's `Fitness` equals the analytic ln L to ≤ 6e-14 nat;
- 200 000 exact draws reproduce every median within 0.006 σ;
- the control verdicts are accepted.

## Submission (2026-10-15, B5c)

- RAL job **410866_[0-929]** (`hpc/batch_cpu/submit_correlated_nd_pilot`): 930 one-run array
  tasks, `%100`, from the private copy `/mnt/ral/jnightin/inference/autofit_inference_b5c`.
  It was pending at submission.
- **Finished 2026-10-16** (wall 4:16): 926 of 930 tasks COMPLETED, 4 OUT_OF_MEMORY at the
  8 G request, all on `corr_gaussian_d50`: task 263 (`nautilus` `n_live_100`, numpy, seed
  3), 273 (`nautilus` `n_live_100`, jax_cpu, seed 3), 304 (`nautilus` `n_live_400`, numpy,
  seed 4) and 383 (`blackjax_nuts_warm` `warmup_200_samples_500`, jax_cpu, seed 3). By the
  human's decision they are not rerun in stage 1; B5c-2 raises their memory or excludes
  them, with the reason recorded. The results stay unpulled in the private copy.
- The first submission, 409957, failed at import in every task: the shared RAL clone had
  been switched by another session. It was cancelled and wrote no row.

## Judged and closed (2026-10-16, B5c-2a, autofit_inference#17)

**Status: complete.** `results/` of 410866 was pulled from the private copy (930 rows; the
8 exact references there are byte-identical to the committed ones) and judged under
`correlated_nd@1` (`results/accounting/correlated_nd_pilot.json`, reconciled with the
committed `sacct` extract):

- **1040 expected = 749 completed rows + 177 failed + 4 `oom` + 0 missing + 110 deferred**;
  930 admitted, 0 refused.
- Under `@1`: **307 accepted, 623 rejected**. The pilot ranks nothing.
- `oom` is a new attempt class. The submit had written cap stubs for the 4 OUT_OF_MEMORY
  tasks, because SLURM's OOM SIGKILL exits 137 under `timeout`. They were rewritten from
  sacct, with MaxRSS 7.6 / 7.7 / 3.1 / 8.4 G at the 8 G request.
- The failures:
  - 80 Emcee/Zeus rows (d20, banana) crashed in the harness's chain diagnostics after the
    search. That bug is fixed.
  - 60 d100 Nautilus rows, which fail at the pin.
  - 10 d100 warm NUTS rows.
  - 27 rows stopped at the 4 h cap (d50 Nautilus `n_live_100`, d50 warm NUTS).

**Calibration and freeze.** The calibration is
[`results/calibration/correlated_nd_wave1.json`](https://github.com/PyAutoLabs/autofit_inference/blob/main/results/calibration/correlated_nd_wave1.json).
`correlated_nd@2` (protocol §11 A2) was frozen in autofit_inference `44c5e77f1fb0` before any
scored row:
- σ-ratio bands are per task. The evidence band is [0.85, 1.1] (79 rows). The posterior
  band is kept at [0.5, 2.0] (1 row, < 20).
- The ESS and R-hat bars are kept.
- 75 timed cells and 8 probe-first cells.
- 21 cells are deferred, each with its reason. They include the OOM cells d50 Nautilus
  `n_live_100` and d50 warm NUTS (by the cap rule) and every d100 Nautilus cell.
- Memory is `max(8 G, ceil(2 × the pilot peak))`: 16 G for d50 Nautilus `n_live_400`,
  17 G for d100 cold NUTS.

## Next

B5c-2b (`draft/research/autofit_inference/search_ext_b5c2b_scored_wave_submit.md`):
realisations 2–3 and their exact references, then the scored-wave manifest (83 cells × 50
seeds × 3 realisations = 12 450 runs) and its probe, then the submit. Nothing is submitted
by this task.
