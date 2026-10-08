# PyAutoInsight contracts

Insight coordinates inference campaigns and pending domain tasks. The project owns
measurements, exporters and storage. Cortex owns run records, observations and human
conclusions. Mind owns bounded implementation issues, PRs and repository claims.
There is no inference conductor and no new scientific execution engine.

## Registry and exchange

`registry.yaml` version `schema: 1` lists instances with `instance`, `repo`,
`summary_path`, `supported_schema`, `dashboard_url`, `library_refs` and
`cortex_project`. Repository identity/location resolves from Mind's `repos.yaml`.
A source is registered once. A fixture demonstrates generic reading without being
registered as a real second adopter. Initial real producer: autolens_inference.

The reader supports `schema: inference-summary`, integer `version: 1` or `2`.
Required envelope keys: project, scope, generated_at, evidence_updated_at,
producer_revision, coverage, records, comparisons, comparison_policy, limitations.
`project` equals the registry's Mind identity. Times are UTC; unknown evidence time
has an explicit reason. Producer revision is the producing code's full commit,
separate from the ingest receipt commit containing the generated file. Null
producer revision requires a reason. `valid_until` is optional; absent means
freshness policy unspecified. Generation time never substitutes for measurement time.
Additive fields are allowed. Breaking versions require consumer support first.

Each record preserves id, parent_run_id, stage, target, dataset, model, pipeline,
sampler, configuration, backend, hardware, precision, seed, dependency_revisions,
execution, scientific, timings, diagnostics, comparison, samples, evidence_paths,
measured_at and archived. Unknown values remain null with recorded limitations or
unknown_reasons. Pipeline parent and stage records are distinct; record counts
are not counts of independent runs.

Execution status and completed markers do not certify convergence or acceptance.
Scientific assessment remains `not_assessed` unless explicitly provided by the
producer's protocol. No universal threshold, default-sampler promotion or best-seed
selection is performed. Failed/stopped/incomplete records remain visible. Historical
project records are labelled archived and separated from current results; the retired
inference programme is never imported. Coverage exclusions preserve invalid rows
with reasons instead of silently losing them. Unknown expected coverage is explicit.

Four clocks (`setup_s`, `sampling_s`, `total_s`, `compile_s`) each have a textual
definition. Null does not mean zero. The reader neither subtracts clocks to derive
setup nor sums stages. Diagnostics carry `status` and `values`. Samples carry
availability and access limitations; safe output paths are hints, not verified
public archive links. Large samples remain in project storage.

Comparisons declare id, records and protocol. The reader refuses changed scientific
target/dataset/model/pipeline/stage/seed identities and incompatible clock definitions.
Unknown controls are not proof of parity. It displays refusals without ratios or
rankings. The initial producer declares target/seed/stage context but no certified
comparison pairs. Detailed original evidence remains linked at the capture commit.

## Version 2: setups and baseline-to-experiment contract

V2 retains every v1 envelope and record field, clock and provenance distinction.
It adds `setups`, `prepared_problems` and explicit conditions on each record.
The complete synthetic [v2 fixture](tests/fixtures/lens_summary_v2.json) illustrates
a SLaM prerequisite stage, a baseline `mass_total[1]` stage and cold/warm/resumed
experiments. Its measurements are test data, not scientific recommendations.

The reader accepts both versions, but a registry row still pins **one exact
version**. Deploy this reader first, then the project producer, then change the
registry pin with its consumer. The live registry remains `inference-summary@1`
in this phase. Rendering and scientific execution are unchanged. There is no
automatic v1 conversion and no inferred baseline, start state or acceptance.

### Identity and ownership

| Object | Required fields | Meaning |
|---|---|---|
| Setup | `id`, `label`, `dataset_family`, `model_family`, `instrument`, `reference_record_id` | Stable navigable setup, e.g. imaging/delaunay/HST; IDs are independent of script paths. Multiple exact configurations can live under the family. |
| Prepared problem | `id`, `setup_id`, `dataset_id`, `model_id`, `priors_id`, `stage`, `baseline_record_id`, `artifacts` | Exact scientific problem shared by baseline and experiments. Model and prior IDs identify frozen definitions, not display names. |
| Run record | All v1 fields plus `setup_id`, `problem_id`, `experiment_protocol`, `initialization`, `environment`, `work` | A particular measurement with its own seed, sampler, hardware, revisions, diagnostics and clocks. |

`instrument` and `reference_record_id` may be null with a sibling `<field>_reason`.
Prepared problem `dataset_id`, `model_id`, `priors_id`, `stage`, and
`baseline_record_id` may likewise be null with reasons. Stage null is appropriate
for standalone toy likelihoods; SLaM uses its actual recorded stage name, not
an alias such as `mass[1]`. Run `setup_id`, `problem_id`, and
`experiment_protocol` may be null with reasons for unmapped historical or
prerequisite/parent records. Every non-null reference must resolve. All lists
have unique IDs. Records must agree with their setup's dataset family/instrument
and their problem's setup, exact dataset and stage.

The project producer owns the assertion that the frozen model/prior definitions
and artifacts actually match the executed analysis. Include their manifests in
the artifacts; Insight validates declarations, not scientific Python objects.
A changed dataset, model, priors, adapt image or other likelihood-affecting
preparation requires a different prepared-problem ID. A sampler change alone
does not. Keep backend, solver/configuration and measured revisions explicit in
the run; a protocol must fix every scientific control it claims to compare.

Prepared `artifacts` and initialization `sources` use the same provenance shape:

```json
{
  "kind": "adapt_image",
  "record_id": "baseline-source",
  "path": "prepared/adapt.fits",
  "revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
```

The path is safe and relative to the producing project repository/storage root;
revision is the full source commit and sha256 identifies exact artifact bytes.
Paths may refer to retained private/gitignored output: this declaration is not
a claim of publicly downloadable or currently available bytes. The project
executor must verify the artifact digest and availability before reuse; Insight
does not fetch artifacts. The source record must resolve. Prepared sources must
belong to the same setup and may come from earlier SLaM stages. An empty artifact
list needs `artifacts_reason` (e.g. unavailable historical state, or a toy model
that needs no adapt products). Unknown evidence is never replaced by current
defaults or another run's artifacts.

`baseline_record_id` identifies the reference run for the prepared problem. It
can retain an archived or unassessed baseline candidate. This **does not select
it as trusted**. The setup's optional `reference_record_id` is an explicit
producer selection: it must resolve to a current, complete, explicitly accepted
baseline of that setup/problem with known dataset/model/prior identities and
`diagnostics.values.max_log_likelihood` plus a nonempty numeric
`max_likelihood_parameters` mapping. Existing `samples` availability and posterior
diagnostics remain separate; a maximum-likelihood match does not prove posterior
recovery. Scientific acceptance is supplied by the project/Cortex protocol,
never inferred by Insight. A missing selected reference needs a reason.

### Sampler start, compilation and caches

`initialization` requires `mode`, a nonempty `recipe` and a `sources` list:

| Mode | Meaning and source requirements |
|---|---|
| `cold` | Start from the prepared priors without reusing baseline best-fit parameters, posterior samples or sampler state. `sources` must be empty. Prepared SLaM adapt products remain allowed. |
| `warm` | Reuse named baseline information, such as positions, posterior particles, covariance or a mass matrix. At least one pinned source is required. |
| `resume` | Continue a previous run from its checkpoint; at least one source must have `kind: checkpoint`. A resumed segment is not a fresh cold or warm measurement. |
| `unknown` | Legacy or incomplete evidence; requires `reason`. Never assumed cold. |

Initialization sources must be other records of the same prepared problem.
Self references and cycles are invalid. A checkpoint snapshot is a distinct
source record; do not overwrite it with the resumed measurement. Priors narrowed
using baseline results change the scientific problem, not merely the start mode.

Each record's `environment` requires `hardware_id`, `compilation` and `cache`.
The project defines a hardware ID that includes device/host resources and
concurrency; it is separate from incidental scheduler job IDs. Unknown hardware
is null with `hardware_id_reason`. Compilation and cache each take `cold`,
`warm`, `not_applicable` or `unknown`; unknown requires `<field>_reason`.
Sampler initialization does not determine either state. A cold sampler can run
with warm compilation, and a warm sampler can pay compilation costs.

### Costs and work units

V2 adds `timings.preparation_s` and `timings.initialization_s`, each nonnegative
seconds or null. Both require entries in `timings.definitions`; null also needs
`<field>_reason` in the timings object. Preparation describes prerequisite work
such as the SLaM stages that built adapt products. Initialization describes
sampler startup/warmup as defined by the producer. Definitions must state the
scope, inclusion in other clocks and whether a resumed clock is cumulative or
segment-only. Never add overlapping clocks or infer unmeasured cost as zero.
The original setup/compile/sampling/fit clocks retain their original definitions.

`work` requires separate `likelihood_evaluations`, `gradient_evaluations`,
`iterations`, `retained_samples` and `effective_sample_size`. Counts are
nonnegative integers; ESS may be a nonnegative real. All may be null with a
sibling `<field>_reason`. `work.definitions` requires a definition for each:
include whether warmup/burn-in is counted, chain/particle aggregation and the
ESS estimator where applicable. Sampler-native iterations are not a common
cross-sampler work unit; no conversion into evaluations is inferred.

### Comparisons and migration

V2 comparison refusals extend v1's target/dataset/model/pipeline/stage/seed and
clock checks. Prepared problem, setup, experiment protocol, backend, precision,
dependency revisions, initialization and environment must match. Problem
dataset/model/prior identities must be known; the comparison protocol must match
the record protocols. Unknown starts or hardware/compilation/cache conditions,
resumptions and archived records are refused as current like-for-like cost
comparisons. Refused groups remain visible with reasons. Differing hardware or
starts can still be browsed as separately labelled evidence; this version does
not certify a cross-condition speed ratio. No acceptance, ranking, best seed or
universal convergence threshold is calculated even when controls match.

Keep original record IDs, parent/stage links, archives and result paths during
migration. Unmapped records retain explicit null bindings and reasons. Empty v2
lists remain a valid "no measurements" state. The producer and executor must
validate model/prior/artifact provenance; the dashboard and assistant consume
the same project-owned catalogue rather than independently reconstructing it.

## Ingest and output

`bin/pyauto-insight fetch` resolves each project branch once and fetches the declared
summary at that full SHA. It validates the contract and project identity, then writes
`receipts/<instance>.json`; a good read also writes `snapshots/<instance>.json`.
A failed fetch never overwrites a last-good capture. Cached evidence retains its
original commit, capture time and evidence time with the new failure visible.
Unchanged fetches preserve capture timestamps. Offline reads validate stored inputs.
Malformed versions, identities, dates, nonfinite numbers and unsafe evidence paths
are invalid, never scientific verdicts. A valid empty feed says no measurements.

`board` emits dashboard.md, dashboard.html, state.json and badge.json. The state
feed uses Brain's cockpit v1 contract, organ `insight`, repo `PyAutoInsight`.
Its updated timestamp describes monitoring output, never a scientific check-in.
Integrity, freshness and scientific assessment remain separate. No invented TTL
applies when the producer has not declared a deadline.

`board --offline` reproduces captures without network. `--from lens=PATH` is an
explicit local preview, labelled with checkout revision and dirty state; it writes
no capture receipts. `check --offline` validates registry, snapshots, migration,
campaigns, dashboard input digests and the Brain state contract. It detects stale
campaign and evidence input renders. It does not query scheduler state.

## Campaign and migration ledgers

`campaigns.yaml` version 1 owns campaigns and tasks. Rows require stable id, title,
status, reviewed date `updated`, next step; task rows name a campaign and safe existing
tasks/ path. Campaigns also retain recent_progress, blockers and job_status. Tracked
active is not a running job. Blocked, parked, needs-decision and needs-slicing remain
open; complete/superseded remain in history but leave the open table.

`migration.yaml` pins source repo/commit, original path and SHA256 for each migrated
task (including a verbatim source fragment where declared). Original bytes are frozen:
subsequent decisions go into check-in reports and ledger fields, not rewritten origin
text. The audit lists retained mixed/library work and authoritative Cortex links.
Destination files must merge before Mind deletes any original; current references
then resolve to Insight. Historical records are not rewritten.

`last_checkin` is null until a real sweep. A timestamp requires a durable report at
`last_checkin_report` under checkins/. CHECKIN.md defines verified-source recording,
changes since prior sweep, missing access and handoffs. A refresh never stamps this
field or changes tasks. The editable prompt always retains the complete sweep even
with campaign-specific direction. Clipboard copies textarea.value with a selectable
fallback. Copying a prompt grants no compute/default/approval authority.

## Workflows

The project publication workflow writes its summary then sends `insight-refresh`
using the existing organisation PAT. Payload source_commit identifies the published
project commit; summary_source_commit identifies producing code/evidence history.
The organ independently resolves its registered branch, records the actual ingest
commit and refreshes the board. Nightly/manual refresh catches missed events.
The receiver explicitly dispatches Pages after its bot commit because GITHUB_TOKEN
pushes do not trigger another workflow. Pages deploys only generated HTML, badge
and state; links continue to point into project repositories.

Before shipping: Ruff, formatting, full pytest and offline contract validation.
Integration CI validates Brain's feed contract. Actual sender/receiver success and
receipt revision are deployment evidence, distinct from mocked workflow tests.

## Setup browser and candidate handoff

Version 2 captures expose project → dataset family → model setup navigation.
Each setup opens a new tab with a stable `?view=setup&instance=…&setup=…`
address. The headline shows only the producer-selected, validator-qualified
reference baseline. Missing acceptance remains explicit; historical runtime is
never promoted into an expected runtime. Sampler records show initialization,
hardware, compilation/cache state and measured clock/work units separately.
Baseline manifests, archived results, comparison refusals and provenance remain
available in disclosures. Unmapped records remain reachable from the project.
Without JavaScript, setup content remains accessible as ordinary disclosures.
Images, when declared, resolve at the captured producer revision.

`sampler_candidates.json` is a manually reviewed public handoff from literature
curation. Each entry records primary paper and official code URLs, review date,
expected uses and limitations, separately stated integration/benchmark status,
and an editable investigation prompt. Update it after an on-demand literature
review; verify source claims and installed search coverage before changing status.
Do not copy private notes or infer measured superiority from a paper. Candidate
prompts propose work through the sampler pipeline; they do not authorize compute.
The candidate file participates in the dashboard input digest. Regenerate the
board after changing it and run the offline check.

The required Chromium navigation check (`python tests/browser_setup.py`, after
installing Playwright and Chromium) covers new-tab routing, mobile width,
unknown routes, history, editable clipboard payloads and the no-JavaScript
fallback alongside the full Python suite.

The results browser groups instrument-specific setup IDs beneath one likelihood
choice, matching Pulse's model list. Implementation is an independent view filter:
JAX and Numba records never share a result panel, and unrecognized backends remain
explicitly unspecified. Imaging Delaunay/Rectangular also expose empty Numba/JAX
filters when there are no measurements; these links claim neither runtime nor
implementation availability. Instrument selection updates the URL within the
opened tab and supports browser history. Existing setup links still resolve.
Routine capture/integrity metadata is available in the machine-readable receipts
and snapshots, not an Evidence details disclosure. Actual stale, failed, cached
and local-preview warnings remain visible. JAX choices carry an explicit (JAX) label. Campaign tables display only
name, recent progress and next steps; the complete ledger remains authoritative.
