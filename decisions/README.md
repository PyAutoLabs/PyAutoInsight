# Decision records

Decision History is a flat, newest-first list below the dashboard's Results.
It is not divided by repository, dataset or likelihood. Entries open readable
GitHub Markdown pages in new tabs.

## Capture a decision

Say **"record this decision"**, or explicitly flag a key campaign decision,
in the ongoing campaign conversation. Follow CHECKIN.md's decision capture
procedure. A dedicated skill is not required: the check-in instructions are
the entry point for both natural-language forms.

Write one canonical `decisions/<id>.md` in the organ leading the campaign.
Use the template below; do not index the template or an undecided draft.
Add the same id, title, date and canonical URL to `decisions.yaml` in each
relevant dashboard. Cross-dashboard entries link to the same page; never copy
the decision prose. The date is the date the human made the decision, not the
board refresh date. Quote it in YAML. IDs are stable lowercase kebab-case.

The index has exactly one `decisions` list; each entry has `id`, `title`,
`date` (YYYY-MM-DD string), and `url` pointing to
`https://github.com/PyAutoLabs/<owning-organ>/blob/main/decisions/<id>.md`.
The owning organ is PyAutoPulse or PyAutoInsight. Its local record must exist
and its heading and Date line must match the index. Publish the canonical
record before adding a link from the other dashboard, then verify that link.
Evidence references within the record should pin commits or immutable results.

Keep old decisions visible. A changed choice gets a new dated record with a
"Supersedes" link; add a "Superseded by" link to the old page without rewriting
its original reasoning. Clarifying factual corrections are dated annotations.
An agent's proposed interpretation is not a human decision. Cortex/project
ledgers remain authoritative for scientific facts and human conclusions;
these pages summarize and cite them. Recording does not implement the choice,
submit compute, change defaults or certify scientific acceptance.

## Record template (not a published decision)

```markdown
# <Decision title>

Date: YYYY-MM-DD
Decision maker: <human>
Decision source: <human statement and durable source link, or dated conversation quotation>

## Campaign
<Goal, motivation and scope across repositories/datasets.>

## Evidence
<High-level findings with pinned links; hardware, precision, model, cold/warm
start and timing definitions where relevant. Include uncertainty and failures.>

## Options considered
<Alternatives and consequential tradeoffs.>

## Decision
<The human's actual choice, its scope and any exceptions.>

## Implications
<Effects on likelihoods, SLaM/inference defaults, compatibility and follow-up
work. Distinguish decided direction from implementation already shipped.>

## Revisit conditions
<Remaining uncertainty and what new evidence would change the choice.>

## History
<Supersedes/superseded-by links when applicable.>
```
