# All inference campaigns in one chat

The editable prompt at the top of the dashboard is the entry point. Use it
unchanged for a complete sweep. A campaign focus or idea supplied before or
after the prompt, or appended inside it, changes emphasis but never removes
the overall sweep. Copying text does not launch a job or grant an approval.
The dashboard is a static evidence view, not a scheduler or a running agent.

## Check-in procedure

1. Fetch Insight, Mind, Cortex and the relevant project default branches; read
   their instructions. Read `campaigns.yaml`, linked task contracts and
   `migration.yaml`. Resolve old Mind paths through that mapping. Read the
   last durable check-in report, if any; `last_checkin: null` means no complete
   sweep has yet been recorded. The initial migration is not a check-in.
2. Inspect current project ledgers, published `inference-summary` feeds,
   relevant issue/PR/release state and Cortex `projects/<key>.md` Now/Runs/Log
   records. Pinned links identify the last reviewed evidence; check current
   branches for later changes. Do not use archived Cortex tasks or rulings as
   a live workflow. Do not revive the retired `inference_programme`.
3. Where authorized access exists, use the existing project's pull/status
   driver to obtain scheduler state and outputs. Record which source revision,
   scheduler query time, job IDs and result/archive locations were actually
   inspected. Otherwise explicitly say unavailable: old `running` ledger rows
   and active campaign labels are not current job evidence. Missing output is
   neither success nor failure. Keep failed/stopped seeds, partial pipelines
   and missing diagnostics or sample archives in the coverage report.
4. Compare with the previous report and give one concise campaign table:
   verified changes, current coordination state, current job evidence,
   blockers and next bounded step. Separate execution completion from
   convergence and human scientific acceptance. Respect declared target,
   dataset, model, sampler, seed and parity identities; never rank incompatible
   targets or cherry-pick the best seed. Keep setup, sampling and total wall
   definitions visible and do not sum overlapping stage timings.
5. Apply the user's ideas and focus to the proposed priority order, retaining
   every open campaign in the sweep. An idea remains a hypothesis. Preserve
   blocked, parked, decision-gated and needs-slicing states until their
   explicit evidence or human decision changes. Check Mind claims before a
   bounded development phase. Use existing project drivers and Brain/faculty
   routes; no new inference conductor is required. A check-in grants no
   compute, default change, scientific threshold, merge or release approval.
6. Write `checkins/YYYY-MM-DDTHHMMSSZ.md` with the template below. Update
   `campaigns.yaml` only with verified coordination changes, dated sources and
   next actions; link the report in each changed row (`checkin_report`). Set
   `last_checkin` to the completed sweep's ISO UTC timestamp and
   `last_checkin_report` to that report. Log inaccessible sources and their
   consequences even if no verified change occurred. Do not advance evidence
   measurement dates or cached ages. A board refresh must not stamp a
   check-in, change task state or imply scientific acceptance.
7. Run `bin/pyauto-insight board --offline` and
   `bin/pyauto-insight check --offline`, then the repository's required CI.
   Persist the report/ledger/generated board through the normal issue/PR
   workflow and report its URL and merge state. Another chat resumes from
   these files, not remembered conversation state.

## Durable report template

```markdown
# Inference check-in — <UTC timestamp>

Previous: <report path or none>
Scope: all open campaigns; optional user focus <verbatim direction>
User decisions: <explicit words and source; none if absent>

## Sources inspected

| Source | Commit / query time | Evidence | Availability |
|---|---|---|---|
| <project / Cortex / PR / scheduler> | <immutable revision or UTC time> | <URL/path> | <verified/unavailable> |

## Campaign sweep

| Campaign | Change since previous | Coordination state | Job evidence | Blocker | Next bounded step |
|---|---|---|---|---|---|

## Coverage and limits

Include failed seeds, partial stages, unknown provenance, missing diagnostics,
sample/archive access limits and stale cached producers. Link scientific
observations and human conclusions in Cortex; do not write competing verdicts.

## Decisions and handoff

Record proposals separately from authorized actions. Link Mind implementation
issues/PRs and completion records. State explicitly whether any compute was
submitted, and under what separate authorization; default is none.
```

## Ownership and migration

Insight owns inference campaign intent, pending domain tasks and their next
steps. `campaigns.yaml` is the live coordination ledger; task IDs are stable.
The open task table includes blocked/parked work and is not an execution queue.
Historical `Status`, `Unattended` or routing headers in preserved task text
are original evidence, not a second independently editable schedule.

The original migrated task bytes are immutable and hashed in `migration.yaml`.
Add subsequent decisions, implementation links and updated next steps to the
ledger and durable reports rather than changing those originals. New tasks
may have their own maintained contract. For mixed campaign maps, completed
phases remain historical and are not reissued; deferred human gates survive.
The EP map's profiling bootstrap/scoping references route to Pulse; library
implementation phases route to Mind. Neither constitutes another organ queue.

Mind retains bounded implementation prompts, issue/PR lifecycle and repository
claims. Reuse existing issues; a broad campaign map is never issued wholesale.
Link the canonical Insight task from a small implementation prompt and link
its completion record back after close-out. Cortex retains authoritative run
records, observations and human conclusions in its current Now/Runs/Log
contract; project ledgers retain detailed experiment evidence and commentary.
Where a historic project document conflicts with that contract, follow Cortex.
No task migration moves samples, outputs or scientific records.

The initial audit in `migration.yaml` records all screened pending Mind
candidates, retained implementation/dependency ownership and pinned source
revisions. Destination files must land before deleting source task files or
removing the migrated ideas line. Keep historical completion records intact;
repair current routing references to canonical Insight URLs after landing.
