# Drop the numba_cpu dense leg from the HST clean-slate campaign

Date: 2026-10-18
Decision maker: James Nightingale
Decision source: inference chat, 2026-10-18, after the 2026-10-18T17:00Z check-in: "lets just drop dense numba we would never use it."

## Campaign
`hst-imaging-mass-samplers` (PyAutoInsight): the clean-slate HST SLaM benchmark at pin
2026.10.17.1, measuring the Nautilus base chain on jax_gpu, jax_cpu and numba_cpu with
dense and sparse inversions, then other samplers on the mass stage.

## Evidence
- RAL array 412563 (`hst_cleanslate_numba_cpu_dense`, `--partition=ral`, 8 CPUs, 48 GB,
  seeds 0-1, both light modes) FAILED 1:0 on both seeds after 57 s on 2026-10-17: two
  Nautilus pool workers died with SIGSEGV on the first `source_pix[1]` likelihood batch,
  MaxRSS 356 MB (not an out-of-memory kill). Rows carry only the shared `source_lp[1]`
  stage with `status: failed: SearchException ...`
  (checkins/2026-10-18T170000Z.md; autolens_inference `results/slam/imaging/hst/*/hpc_a100_numba_cpu_dense_fp64__cleanslate_2026_10_17/`).
- The sibling numba_cpu sparse array 412565 with the identical pool was still running
  after 21 h, so the crash is specific to the dense numba likelihood under forked workers.
- The dense inversion on CPU is already covered by the jax_cpu dense leg (412539), and
  numba on CPU in practice is used with the sparse (w_tilde) inversion.

## Options considered
- Rerun numba_cpu dense serially (`--cores 1`) or with `NUMBA_THREADING_LAYER=workqueue`.
- Drop the leg: no rerun, no row.

## Decision
Drop the numba_cpu dense leg from the campaign. No rerun. The failed rows stay as
history; the leg is not a gap in the parity table.

## Implications
- The CPU base of the campaign is jax_cpu dense, jax_cpu sparse and numba_cpu sparse.
- No fix is owed for the SIGSEGV in this campaign. The crash is still worth a note where
  numba dense is documented, since a user with `number_of_cores > 1` would hit it.
- Submit script `hpc/batch_cpu/submit_hst_cleanslate_numba_cpu_dense` is not to be
  resubmitted under this campaign.

## Revisit conditions
A use case for numba with the dense inversion on CPU, or a PyAutoFit/PyAutoLens change
that makes the forked-worker numba dense path the default somewhere.

## History
None.
