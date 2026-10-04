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

The reader supports `schema: inference-summary`, integer `version: 1`.
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
