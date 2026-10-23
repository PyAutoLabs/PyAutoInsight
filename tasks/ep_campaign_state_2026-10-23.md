# EP campaign — state reconciliation (2026-10-23)

Companion to `tasks/ep_campaign.md`. That file is a byte-preserved migration
original (`migration.yaml` pins its SHA256 and `pyauto-insight check` fails if it
changes), so its "State (updated 2026-09-10)" column stays as history and the
2026-10-23 state is recorded here instead. Read the two together: the phase
table below appends to, and does not replace, the original State cells.

Sources: PyAutoCortex `origin/main` 5fa4eb98 (`projects/analytic_gaussian.md`,
`ep_toy_gaussian.md`, `slope_hierarchy_scale.md`, `ic50_workspace.md`, "Now"
sections) and the PyAutoFit merge/release history. No live scheduler was
queried; nothing here is a job state.

## Shipped since the 2026-09-10 table

All merged and released in PyAutoFit 2026.10.7.1:

| PR | What | Campaign effect |
|----|------|-----------------|
| #1632 / #1634 | EMFILE: one Pool per single-core Dynesty fit | ep_toy_gaussian wave-2 prerequisite (wave 1 died on EMFILE) |
| #1643 / #1644 / #1645 | Per-factor-search wrapper overhead 2.45 s → ~0.95 s | record `complete/2026/09/ep-factor-search-overhead.md` |
| #1655 | `ProjectionException` recovery in EP `factor_step` | the IC50 N=50 projection-assert cure |
| #1656 | `LaplaceOptimiser(projection="moments")` | the hierarchical-scatter cure; `analytic_gaussian.py` un-parked PARITY 41/41; record `complete/2026/09/ep-moment-projection.md` |

The shared RAL PyAutoFit mirror is still 404b3e5f7 (2026-09-27), kept frozen for
euclid_dr1; it lacks #1655 and #1656, so the slope_hierarchy_scale and ic50
reruns below need a private PyAutoFit checkout on RAL (ep_toy_gaussian wave 2
only needs #1632/#1634, already in the mirror; a private checkout is optional
there). Project `output/` was vaulted to `z_vault/` on
2026-10-14.

## Phases (State (updated 2026-10-23))

| # | Phase | 2026-10-23 addendum to the original State cell |
|---|-------|------------------------------------------------|
| 1 | Analytic Gaussian benchmark → Cortex `analytic_gaussian` | Wave 1 (342413, 200 seeds at N=5) is accepted as the baseline (R-20260910-04): autofit EP exact on the Gaussian leg, leg B sigma misses 78/200 as pre-registered, collapse 0/200. The moment-matching cure shipped as #1656 and un-parked `analytic_gaussian.py`. On criterion 2, astra and an independent Opus review favour an under-calibrated mu threshold and flag the per-site sigma>0 clip (`analytic_ep_minimal.py:333`) as the one audit target. **Next:** run the planned mu-threshold diagnostic (`archive/tasks/analytic_gaussian/minimal_ep_legb_mu_threshold.md`) on a passing, an edge and the worst mu seed; N=25 stays written but unsubmitted until it lands. |
| 1b | #1405 collapse toy at N=50 → Cortex `ep_toy_gaussian` | Wave 1 (342639 + 342640_[0-2]) failed on infrastructure: EP x3 on EMFILE (cured by #1632/#1634, in the RAL mirror), NUTS on OOM at 8 GB while XLA compiled the 50-factor window adaptation. Wave 2 is prepared, not submitted: sample `n50_seed42_w2` still needs its `toy.SAMPLES` entry, submit_nuts raised to 64 GB, submit_ep unchanged at 8 GB. The N=50 collapse question is unanswered. **Next:** human go, add the sample entry, push and submit NUTS then EP with `SAMPLE=n50_seed42_w2` exported. |
| 2 | Scatter-collapse cure or caveat | No change; the cure follow-on landed as #1656 (above). |
| 3 | Graphical JAX scaling → Cortex `slope_hierarchy_scale` | N=25 graphical baselines are in: joint NUTS (342350_0) mean 1.994 [1.976, 2.014], sigma 0.087 [0.074, 0.104] vs truth 2.0 / 0.1; per-lens naive parent 1.999 / 0.089. Its summary JSON still needs writing offline from `samples.csv` (now under `z_vault/sample_n25_seed42`). The EP arm returned the prior on the Laplace projection (343299: hierarchical factor 0/50 SUCCESS). **Next (human-gated):** rerun the N=25 EP arm with `projection="moments"` on a private PyAutoFit checkout and compare its scatter against the NUTS baseline. |
| 1b/3 | Check-in (EP arms of 1b and 3) | The 2026-09-24 items are resolved upstream: #1632/#1634 and #1643–#1645 are released in 2026.10.7.1, and the moment-matching decision was taken (#1656). What remains is the two human-gated reruns in rows 1b and 3. |
| 4 | IC50 EP end-to-end + scale ladder → Cortex `ic50_workspace` | The ladder is in: EP passes N=5/10/25 (coef_mean within 3σ; 26/50/140 s per sweep) and died at N=50 on a projection assert, now cured by #1655. Graphical is cheaper but overconfident beyond N=25; EP `hill_coef` widths are not yet comparable because `util.py` reports factor-message widths. **Next (human-gated):** rerun the EP ladder on a private PyAutoFit checkout with output on and a fixed seed, report `hill_coef` from the mean field, then give `ep_lbfgs_jax` a witness as the scale lever. |
| 5 | Diagnostics sufficiency checkpoint | Two wave-1 ruling findings shipped on 2026-10-23 (below): PyAutoFit#1711/#1712 (NO_CHANGE is a converged update; criterion 6 amended) and #1713/#1714 (non-finite evidence terms named once per fit, explicit NaN, `evidence_nonfinite:` diagnostics line). Remaining: the loggaussian moments defect and the tail-stable `log_partition` cure, both the human's call. |
| 6 | Profiling | No change recorded here. |

## Wave-1 findings follow-ups (2026-10-23)

The three findings of the analytic_gaussian wave-1 ruling, as Mind prompts:

| Finding | Prompt | Size / priority | State |
|---------|--------|-----------------|-------|
| EP counts zero-iteration Laplace convergence (NO_CHANGE) as a stale/skipped update | `complete/2026/10/ep-zero-success-factors.md` | tier glance | **Shipped 2026-10-23**: PyAutoFit#1711 closed, #1712 merged (pending-release), autofit_workspace_test#115 merged, PyAutoCortex#75 (criterion 6 counts SUCCESS or NO_CHANGE) merged. Verdict: NO_CHANGE-only prior factor = converged update (closed-form match 1e-4); BAD_PROJECTION-only hierarchical factor = #1405 state cured by moments. |
| NaN in EP evidence accumulation (invalid value) | `complete/2026/10/ep-evidence-nonfinite.md` | medium | **Shipped 2026-10-23**: PyAutoFit#1713 closed, #1714 merged (pending-release), autofit_workspace_test#116 merged. Readout-only defect: an accepted truncated-normal scatter message ~19 sigma into its tail underflows `log_partition` to −inf (mode projection only); posterior bit-identical. The library now names the term once per fit and returns an explicit NaN. |
| `TruncatedNormalMessage.log_partition` underflows in the far tail (the cure of the term above) | `draft/bug/autofit/truncated_normal_log_partition_tail_underflow.md` | small / judge | Filed 2026-10-23 from #1713; message maths — the human's decision |
| Moments projection mishandles the transformed loggaussian scatter (keeps `analytic_gaussian_priors.py` parked) | `draft/bug/autofit/ep_moments_loggaussian_transformed_scatter.md` | small | Filed in Mind; overlaps the priors-tracker Jacobian decisions PyAutoFit#1498 / #1331 — the human's call |

`draft/feature/autofit/ep_lbfgs_jax.md` remains the IC50 scale lever (phase 4).
