# HST imaging mass stage: Nautilus base on CPU and A100, with and without linear lens light

Type: research
Target: autolens_inference
Campaign: hst-imaging-mass-samplers
Issue: none yet
Filed: 2026-10-17

## Intent

Establish a Nautilus reference for the SLaM `mass_total[1]` stage on the simulated HST
imaging cell, on CPU and on the A100 (RAL), in two lens-light modes: the current one, where
the lens light is a linear MGE basis solved inside the inversion, and one with the linear
light removed. These runs become the frozen problems that the sampler waves
(`tasks/hst_mass_samplers_wave1.md`) are measured against.

## Identity

- Dataset: the simulated HST cell, `dataset/imaging/hst` in autolens_inference.
- Pipeline: the 5-stage SLaM chain, `scripts/imaging/rectangular/baseline_slam.py`.
- Base variant: `slam_base`, rectangular 28x28 mesh, `al.reg.Adapt`.
- Mass stage: as built in `scripts/misc/slam/_runner.py` `mass_total()`. A `PowerLaw` mass
  is chained from the `source_pix` `Isothermal` with the mass centre unfixed. The lens light
  is an instance of the `light[1]` MGE basis of linear Gaussians, so its intensities are
  solved inside the inversion at every evaluation.
- Config grammar: `{local,hpc_a100}_{jax_cpu,numba_cpu,jax_gpu}_{dense,sparse}_{fp64,mp}`.

## Phases

0. Land the existing rows. Done: autolens_inference
   [PR #23](https://github.com/PyAutoLabs/autolens_inference/pull/23) (open, pending merge).
1. Bounded development through Mind `start_dev`: a lens-light mode as a run variant of the
   runner, with prerequisites resumed from the `slam_base` output trees, and
   `--export-prepared` for both light modes.
2. Compute, decision-gated: on the A100, `mass_total[1]` with fixed light, dense and sparse,
   seeds 0-1, plus the prepared-problem export; the CPU base legs per the backend decision,
   on `--partition=ral` only, with a stated containment.
3. Sampler waves on the frozen problems: `tasks/hst_mass_samplers_wave1.md`.

## Existing evidence

From the 2026-09-24 re-runs (PR #23), `slam_base`, seed 0 / seed 1, search wall in seconds:

| config | chain | mass_total[1] wall | mass_total[1] log Z | max abs Δσ at mass_total[1] | resumed stage |
|---|---|---|---|---|---|
| hpc_a100_jax_gpu_dense_fp64 | 2,468 / 2,365 | 562 / 521 | 31,589.22 / 31,590.06 | 1.52 / 0.55 | none |
| hpc_a100_jax_gpu_sparse_fp64 | 3,930 / 3,915 | 837 / 825 | 31,597.52 / 31,594.05 | 1.98 / 1.20 | none |
| hpc_a100_numba_cpu_sparse_fp64 | 168,824 / 177,740 | 44,221 / 50,086 | 31,592.05 / 31,595.97 | 1.30 / 3.18 | source_pix[1] |

The clean CPU `mass_total[1]` walls (44,221 / 50,086 s, `numba_cpu` sparse) against A100
dense (562 / 521 s) are observations on one dataset with two seeds. The CPU chain walls span
more than one attempt because the array was requeued. The A100 Nautilus base with linear
lens light already exists as these rows; the CPU base exists only as `numba_cpu` sparse.

## Decisions pending

1. CPU backend for the base: `jax_cpu` (recommended, because the NUTS/SMC experiment path
   requires a JAX-frozen analysis) or `numba_cpu` (completes the parity row).
2. Meaning of "linear light removed": fixed ordinary light profiles with intensities from
   `light[1]` (the plan recorded in Cortex), or lens-light subtraction from the image.
3. Seed count.

## Authorisation

This task authorises nothing: no compute, no default change. Opened 2026-10-17 from the
human's direction in the Insight chat.
