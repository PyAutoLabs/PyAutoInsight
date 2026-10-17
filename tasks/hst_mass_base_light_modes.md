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
  decision 2026-10-17). Later the same day the human added ral `numba_cpu` dense and
  sparse on 8 CPUs, sharing the `jax_cpu` dense `source_lp[1]` (see "Shared stage rule").
- Seeds: 0 and 1 for the base.
- Job shape: one job per (backend, inversion, seed), producing both light-mode rows from
  one chain.
- CPU containment: CPU jobs run on `--partition=ral` only, with 8 CPUs per job, and each
  submission states its containment (array size, concurrency cap and wall limit) before
  it is authorised.
- Config grammar: `{local,hpc_a100}_{jax_cpu,numba_cpu,jax_gpu}_{dense,sparse}_{fp64,mp}`.

## Shared stage rule (numba_cpu legs)

The numba_cpu chains do not fit `source_lp[1]`. They load the completed `jax_cpu` dense fit
of the same seed (`--stages-from hpc_a100_jax_cpu_dense_fp64:source_lp`,
autolens_inference#32). That stage is parametric and has no inversion, so both CPU backends
fit the same likelihood there, and the numba and jax_cpu chains are identical through
stage 1. Both numba legs share the dense stage, including the sparse leg.

- Provenance:
  - In each numba row, the `source_lp[1]` entry carries `shared_from_config` and
    `fitted_backend: jax_cpu`, and keeps that fit's wall and evals for the record.
  - The row's `chain_wall_s` sums only the stages the numba job fitted, and
    `chain_wall_excludes` names the shared stage.
  - A numba chain wall is never compared with a jax_cpu chain wall that includes stage 1.
  - Stage 1 is not a numba measurement and is never cited as one.
- Never a refit: when the stage is not complete, the runner exits 3 and fits nothing. Each
  job waits in-job for the stage first (`hpc/wait_for_stage.sh`: 5 min polls, 8 h cap,
  exit 4 on timeout).
- Only `source_lp` may be shared. A pixelized stage's inversion is what the backend
  comparison measures.

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
   **Submitted 2026-10-17T16:45:58-16:46:08Z** (human-authorised "go on 2"), pin
   `/mnt/ral/jnightin/inference/pins/2026.10.17.1` (tag commits verified), output root
   `output/cleanslate_2026_10_17`, results tag `cleanslate_2026_10_17`, prepared export
   `output/prepared/cleanslate_2026_10_17/<config>/seed_<n>/<variant>/`:

   | array | submit | partition | node / device |
   |---|---|---|---|
   | 412535 | `submit_hst_cleanslate_jax_gpu_dense` | gpu | euclid-ral-gpu-1, gres/gpu:a100=1 |
   | 412537 | `submit_hst_cleanslate_jax_gpu_sparse` | gpu | euclid-ral-gpu-1, gres/gpu:a100=1 |
   | 412539 | `submit_hst_cleanslate_jax_cpu_dense` | ral | euclid-ral-compute-10-1 |
   | 412541 | `submit_hst_cleanslate_jax_cpu_sparse` | ral | euclid-ral-compute-10-1 |

   All four (seeds 0-1) were RUNNING at 16:47Z and had started a fresh `source_lp[1]` under
   the pin.
2b. numba_cpu base legs, human-authorised 2026-10-17 (in-job wait, submit now):
   `submit_hst_cleanslate_numba_cpu_{dense,sparse}`.
   - Setup: `ral` only, 8 CPUs, 48 GB / 64 GB, seeds 0-1, `--lens-light both`, the same pin,
     output root, results tag and prepared export as phase 2, config names
     `hpc_a100_numba_cpu_{dense,sparse}_fp64`.
   - Shipped in autolens_inference#32 (issue #31, merge b91ce9c).
   - **Not yet submitted.** The RAL checkout's fast-forward to b91ce9c was cut off by a
     timeout mid-checkout. HEAD is still dabb652, and the files the pull had already written
     are untracked or modified. They were verified identical to b91ce9c, plus one empty
     file. A plain `--ff-only` now refuses, and completing it needs a human-run
     `git reset --mixed b91ce9c && git checkout -- .` in that checkout. Then submit with
     `hpc/sync submit --cpu submit_hst_cleanslate_numba_cpu_dense` (and `_sparse`).
3. Sampler waves on the frozen problems: `tasks/hst_mass_samplers_wave1.md`.

## Decisions

Recorded in the Insight chat on 2026-10-17, in the human's words:

- Direction: "Let's do this as a fresh start we did kind of start a campaign but weve done
  lots of improvements since warranting a clean slate."
- Clean slate: "Yes, supersede and re-run on the pin".
- CPU backend: "jax_cpu, dense + sparse".
- Light mode: "Fix lens light to ordinary profiles".
- numba_cpu base (later on 2026-10-17): add numba_cpu legs on 8 CPUs that "spawn off" the
  jax_cpu `source_lp[1]`. The human chose an in-job wait for that stage and an immediate
  submit, with rows marking the stage as shared and excluding its wall from the numba chain
  wall.

## Acceptance

Row completion is execution completion only. It is not convergence assessment and not
scientific acceptance; human readings of the base belong in the Cortex ledger for
autolens_inference.

## Authorisation

This task authorises nothing: no compute, no default change. Phase 1 shipped through Mind
`start_dev` (autolens_inference#26); phase 2 was separately authorised by the human on
2026-10-17 and submitted as above. The numba_cpu legs (2b) shipped in autolens_inference#32
under the human's 2026-10-17 authorisation, and are awaiting submission.
