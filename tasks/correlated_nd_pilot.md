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

This task authorises nothing further. Pulling, judging and the `correlated_nd@2` freeze
are B5c-2.

## Next (B5c-2)

1. Pull the pilot's rows (`results/` only) and judge them under `correlated_nd@1`; settle
   the 4 OOM cells (more memory or excluded).
2. Calibrate the PLACEHOLDERs and timeouts, then freeze `correlated_nd@2` before any
   scored row.
3. Submit the scored wave: 50 seeds × realisations 1–3 × every non-deferred cell.
