# HST imaging mass stage: sampler comparison, wave 1

Type: research
Target: autolens_inference
Campaign: hst-imaging-mass-samplers
Issue: none yet
Filed: 2026-10-17
Reframed: 2026-10-17 (clean slate, human decision)

## Intent

Measure which samplers find the `mass_total[1]` answer on the simulated HST imaging cell,
how reliably, and at what cost, from a cold start, on the same frozen problem. The frozen
problems come from the pinned clean-slate base in `tasks/hst_mass_base_light_modes.md`
(PyAuto release 2026.10.17.1): both light modes (linear and fixed lens light), on both
devices (A100 `jax_gpu` and ral `jax_cpu`) where the sampler supports them.

## What exists

- `scripts/misc/experiments/run.py` in autolens_inference runs `nautilus`, `emcee`, `nuts`
  and `smc` on a verified prepared problem.
- `nuts` and `smc` require a JAX-frozen analysis. Because the CPU base runs on `jax_cpu`,
  the CPU prepared problem also enables NUTS and SMC on CPU.
- No prepared problem has been exported yet. The export depends on phases 1 and 2 of
  `tasks/hst_mass_base_light_modes.md`. The 2026-09-24 rows are superseded history and do
  not supply a frozen problem.

## Candidates

From the Brain samplers faculty: the promoted searches Nautilus, NSS, DynestyStatic,
DynestyDynamic, Emcee, Zeus, BlackJAXNUTS and SMC. MLE families are a different task and
are not ranked against posterior samplers.

## Acceptance considerations

- Agreement with the Nautilus reference posterior from the pinned base and with the truth.
- Convergence diagnostics appropriate to each sampler family.
- At least 3 seeds before any reliability statement.
- Cost as wall per converged answer, with setup, sampling and total wall kept separate.
- Never rank incompatible runs (different problem, light mode, device, release or protocol).
- Execution completion is never scientific acceptance.

## Status

needs-slicing. Depends on the frozen `mass_total[1]` problems from
`tasks/hst_mass_base_light_modes.md`. The sampler menu, settings, seeds and devices are not
yet sliced.

## Authorisation

This task authorises nothing: no compute, no default change. Opened 2026-10-17 from the
human's direction in the Insight chat; reframed the same day for the clean slate.
