# HST imaging mass stage: sampler comparison, wave 1

Type: research
Target: autolens_inference
Campaign: hst-imaging-mass-samplers
Issue: https://github.com/PyAutoLabs/autolens_inference/issues/27 (closed)
PR: https://github.com/PyAutoLabs/autolens_inference/pull/28 (merged, dabb652)
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

## Slice (wave 1, 2026-10-17)

Wave id `cleanslate_2026_10_17_wave1`; the arm table is data in autolens_inference
`scripts/misc/experiments/wave.py`.

- **Problems:** the frozen `mass_total[1]` problems of base seed 0, both light modes
  (`slam_base`, `slam_base_lightfixed`), read from
  `output/prepared/cleanslate_2026_10_17/<config>/seed_0/<variant>/manifest.json`. The
  problem id is read from the manifest at run time; the leaf refuses any identity, artifact
  digest or library-revision mismatch, and any existing run id.
- **Configs:** `hpc_a100_jax_gpu_dense_fp64` (A100, hardware id `ral-a100-1gpu-4cpu`,
  `hpc/batch_gpu/submit_hst_cleanslate_mass_samplers_jax_gpu_dense`, `0-23%4`, 6 h
  containment) and `hpc_a100_jax_cpu_dense_fp64` (`ral`, `ral-cpu-8cpu`,
  `hpc/batch_cpu/submit_hst_cleanslate_mass_samplers_jax_cpu_dense`, `0-23%6`, 24 h
  containment). Both pinned to 2026.10.17.1.
- **Samplers, all `--start cold --compilation cold --cache unknown`:** `nautilus --live 150
  --batch 20` (the control, the base stage's own settings); `emcee --walkers 50 --steps
  2000`; `nuts --chains 1 --warmup 500 --steps 1000`; `smc --particles 256 --steps 1000`.
- **Seeds:** sampler seeds 0, 1, 2; 4 x 3 x 2 = 24 arms per config, indexed seed-major
  (index = seed x 8 + variant x 4 + sampler), so the throttle starts one probe arm of each
  sampler first.
- **Run ids:** `cs1017_<config>_<variant>_<sampler>_s<seed>`; rows land in
  `results/searches/experiments/<run id>.json`, catalogued under their `problem_id` with no
  ranking. `wave.py --account --config <config>` reports each arm as row, failed or missing.
- **Out of wave 1:** NSS, DynestyStatic/Dynamic and Zeus need runner support first (wave 2).

## Jobs

- **GPU wave:** array **412543** (`submit_hst_cleanslate_mass_samplers_jax_gpu_dense`,
  `0-23%4`, 6 h containment, gpu), submitted 2026-10-17T16:46:15Z with
  `--dependency afterok:412535_0`: it starts when seed 0 of the GPU dense base array
  (412535) completes cleanly, because the base-seed-0 problems are the only ones the wave
  reads. squeue at 16:47Z: PD (Dependency).
- **CPU wave:** waits for the CPU dense base rows (days), then the same submit with `--cpu`.

## Status

running. Sliced and shipped in autolens_inference#28 (issue #27); witnessed on the euclid
test-mode cell (both light-mode problems exported, all 24 arms `--validate-only` through the
resolver). The GPU wave 412543 is queued behind base array 412535 seed 0; the base arrays
412535, 412537 (gpu) and 412539, 412541 (ral) run since 2026-10-17T16:46Z.

## Authorisation

The human authorised on 2026-10-17 the GPU wave's submission `afterok` on the phase-2 GPU
dense base array ("do whatever is needed to sort 3 and get some runs going"). The CPU wave
is not yet authorised to be queued ahead of the CPU base rows. Execution completion is never
scientific acceptance.
