# HST imaging mass stage, clean slate: Nautilus base on A100 and jax_cpu, linear and fixed lens light

Type: research
Target: autolens_inference
Campaign: hst-imaging-mass-samplers
Issue: none yet
Filed: 2026-10-17
Reframed: 2026-10-17 (clean slate, human decision)

## Intent

Establish a Nautilus reference for the SLaM `mass_total[1]` stage on the simulated HST
imaging cell, measured from scratch at a pinned PyAuto release, on the A100 (RAL) and on
CPU with `jax_cpu`, in two lens-light modes: linear lens light solved inside the inversion,
and lens light fixed to ordinary profiles. These runs become the frozen problems that the
sampler waves (`tasks/hst_mass_samplers_wave1.md`) are measured against.

This is a fresh start. The 2026-09-24 re-run rows in autolens_inference
[PR #23](https://github.com/PyAutoLabs/autolens_inference/pull/23) and the campaigns
`slam-hst-base` and `slam-hst-delaunay` are superseded history; nothing here resumes from
their output trees.

## Identity

- Release pin: PyAuto 2026.10.17.1 (PyAutoLens tag v2026.10.17.1, released 2026-10-17).
  Every row records the five library revisions (PyAutoArray, PyAutoGalaxy, PyAutoLens,
  PyAutoFit, PyAutoNerves) and its SLURM job id.
- Dataset: the simulated HST cell, `dataset/imaging/hst` in autolens_inference.
- Pipeline: the 5-stage SLaM chain, `scripts/imaging/rectangular/baseline_slam.py`, run
  from scratch in fresh output trees.
- Base variant: `slam_base`, rectangular 28x28 mesh, `al.reg.Adapt`.
- Mass stage: as built in `scripts/misc/slam/_runner.py` `mass_total()`. A `PowerLaw` mass
  is chained from the `source_pix` `Isothermal` with the mass centre unfixed.
- Two light modes of `mass_total[1]`:
  - linear: the lens light is an instance of the `light[1]` MGE basis of linear Gaussians,
    and its intensities are solved in the inversion at every evaluation;
  - fixed: the lens light is ordinary profiles with intensities taken from the `light[1]`
    maximum-likelihood fit, through the fit's linear-to-ordinary conversion, so the
    inversion carries no lens-light columns.
  Both modes use the same dataset, the same mask and the same priors on mass and source.
- Backends: A100 `jax_gpu` dense and sparse, and ral `jax_cpu` dense and sparse (human
  decision 2026-10-17). `numba_cpu` is not in this campaign.
- Seeds: 0 and 1 for the base.
- Job shape: one job per (backend, inversion, seed), producing both light-mode rows from
  one chain.
- CPU containment: CPU jobs run on `--partition=ral` only, with 8 CPUs per job, and each
  submission states its containment (array size, concurrency cap and wall limit) before
  it is authorised.
- Config grammar: `{local,hpc_a100}_{jax_cpu,jax_gpu}_{dense,sparse}_{fp64,mp}`.

## Phases

0. Land the existing rows. Done: autolens_inference
   [PR #23](https://github.com/PyAutoLabs/autolens_inference/pull/23). History only; those
   rows are not the base of this campaign.
1. Bounded development through Mind `start_dev`:
   - lens-light mode as a run variant, `--lens-light linear|fixed|both`, where fixed means
     ordinary profiles with intensities from the `light[1]` fit;
   - both light-mode rows produced from one chain;
   - `--export-prepared` for both light modes;
   - the five library revisions and the SLURM job id recorded in every row;
   - submit scripts for A100 dense and sparse and for ral `jax_cpu` dense and sparse,
     against a private pinned checkout of release 2026.10.17.1;
   - the prior identity of the frozen model, including whether the 1e-3 prior centring
     (`tasks/drop_1e3_prior_centring_after_631.md`) is dropped, stated before the pin.
2. Compute, decision-gated and separately authorised: the base above (2 devices x 2
   inversions x 2 seeds, both light modes per job) plus the prepared-problem exports.
   Nothing is submitted.
3. Sampler waves on the frozen problems: `tasks/hst_mass_samplers_wave1.md`.

## Decisions

Recorded in the Insight chat on 2026-10-17, in the human's words:

- Direction: "Let's do this as a fresh start we did kind of start a campaign but weve done
  lots of improvements since warranting a clean slate."
- Clean slate: "Yes, supersede and re-run on the pin".
- CPU backend: "jax_cpu, dense + sparse".
- Light mode: "Fix lens light to ordinary profiles".

## Acceptance

Row completion is execution completion only. It is not convergence assessment and not
scientific acceptance; human readings of the base belong in the Cortex ledger for
autolens_inference.

## Authorisation

This task authorises nothing: no compute, no default change. Phase 1 needs Mind
`start_dev`; phase 2 needs a separate compute authorisation.
