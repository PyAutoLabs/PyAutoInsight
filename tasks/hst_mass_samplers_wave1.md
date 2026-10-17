# HST imaging mass stage: sampler comparison, wave 1

Type: research
Target: autolens_inference
Campaign: hst-imaging-mass-samplers
Issue: none yet
Filed: 2026-10-17

## Intent

Measure which samplers find the `mass_total[1]` answer on the simulated HST imaging cell,
how reliably, and at what cost, from a cold start, on the same frozen problem. Both lens-light
modes from `tasks/hst_mass_base_light_modes.md`, and both devices where the sampler supports
them.

## What exists

- `scripts/misc/experiments/run.py` in autolens_inference runs `nautilus`, `emcee`, `nuts`
  and `smc` on a verified prepared problem.
- `nuts` and `smc` require a JAX-frozen analysis.
- No prepared problem has been exported yet. The export depends on phase 1 and 2 of
  `tasks/hst_mass_base_light_modes.md`.

## Candidates

From the Brain samplers faculty: the promoted searches Nautilus, NSS, DynestyStatic,
DynestyDynamic, Emcee, Zeus, BlackJAXNUTS and SMC. MLE families are a different task and
are not ranked against posterior samplers.

## Acceptance considerations

- Agreement with the Nautilus reference posterior and with the truth.
- Convergence diagnostics appropriate to each sampler family.
- At least 3 seeds before any reliability statement.
- Cost as wall per converged answer, with setup, sampling and total wall kept separate.
- Never rank incompatible runs (different problem, light mode, device or protocol).

## Status

needs-slicing. Depends on the frozen `mass_total[1]` problems from
`tasks/hst_mass_base_light_modes.md`. The sampler menu, settings, seeds and devices are not
yet sliced.

## Authorisation

This task authorises nothing: no compute, no default change. Opened 2026-10-17 from the
human's direction in the Insight chat.
