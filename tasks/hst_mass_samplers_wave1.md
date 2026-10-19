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
  `output/autolens/prepared/<config>/seed_0/<variant>/manifest.json` (flat layout since
  2026-10-19, autolens_inference#36; originally `output/prepared/cleanslate_2026_10_17/...`). The
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
  `--dependency afterok:412535_0`. It started around 17:46Z, when seed 0 of the GPU dense
  base array (412535) completed 0:0. Attempt 1 outcome below.
- **CPU wave:** waits for the CPU dense base rows (412539), then the same submit with
  `--cpu`. Not yet authorised to be queued.

## Attempt 1 outcome (GPU wave 412543, read 2026-10-17T19:40Z)

Read by the architect from RAL sacct, squeue and the job logs. Arm index = seed x 8 +
variant x 4 + sampler (nautilus 0, emcee 1, nuts 2, smc 3).

| arm class | arms | outcome | row |
|---|---|---|---|
| nautilus | 0, 4, 8, 12, 16 | `mass_total[1]` fit completed ("Search complete, returning result"; arm 0 about 13 min of job time), then FAILED in the row writer | none; output trees exist |
| emcee | 1, 5 | fit completed (arm 1 about 37 min of job time), then FAILED in the row writer | none; output trees exist |
| emcee | 9, 13, 17 | still RUNNING at 19:40Z | not yet |
| nuts | 2, 6, 10, 14 | FAILED: `JaxRuntimeError: RESOURCE_EXHAUSTED: Out of memory while trying to allocate 385.32GiB [jit_log_l]` | failed-status row written |
| smc | 3, 7, 11, 15 | FAILED: out of memory allocating `48.45GiB [jit_scan]` | failed-status row written |
| all samplers | 18-23 | cancelled by the architect at 19:40Z while pending | none |

The row-writer failure is `scripts/misc/experiments/run.py` line 350:
`TypeError: keys must be str, int, float, bool or None, not tuple`. The pinned PyAutoFit
returns tuple-keyed parameter names, and the writer passes them to JSON unchanged. This is
a writer fault after the fit, not a sampler failure. No timing, convergence or
posterior statement is drawn from attempt 1.

A fix task is filed in Mind:
`draft/bug/autolens_inference/wave1_row_writer_tuple_keys_and_gpu_oom_reslice.md`. It
fixes the writer, re-runs nautilus and emcee as attempt 2, and defers NUTS and SMC with
the OOM evidence. Another worker executes it; attempt-2 job ids are not recorded here yet.

## NUTS and SMC deferral (proposed)

Proposed reading, not a decision: on the A100 at the wave-1 settings, the NUTS
`jit_log_l` allocation (385.32 GiB) and the SMC `jit_scan` allocation (48.45 GiB) exceed
the device memory. NUTS and SMC are proposed to sit out attempt 2 and return in a re-sliced
arm (smaller batch or particle count, or the CPU wave) once the memory shape of each is
understood. The OOM messages above are the evidence. The human decides the re-slice.

## Status

blocked. Attempt 1 failed on every arm in two classes: the row writer after completed
nautilus and emcee fits, and A100 OOM for NUTS and SMC. Blocked until the writer fix in
the filed Mind task merges; attempt 2 then re-runs nautilus and emcee. Sliced and shipped
in autolens_inference#28 (issue #27); witnessed on the euclid test-mode cell (both
light-mode problems exported, all 24 arms `--validate-only` through the resolver).

## Authorisation

The human authorised on 2026-10-17 the GPU wave's submission `afterok` on the phase-2 GPU
dense base array ("do whatever is needed to sort 3 and get some runs going"). The CPU wave
is not yet authorised to be queued ahead of the CPU base rows. No human decision on attempt 2
or on the NUTS/SMC re-slice is recorded yet. Related human decisions of 2026-10-17 on the
base: numba_cpu base on 8 CPUs, sharing the jax_cpu `source_lp[1]` with an in-job wait and
an immediate submit, rows marking the stage shared and excluding its wall from the numba
chain wall. Execution completion is never scientific acceptance.
