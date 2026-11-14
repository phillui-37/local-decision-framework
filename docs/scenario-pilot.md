# Wider usage without stretching the contract

Local Decision Framework exposes single-claim and batch claim-check tools. A batch
returns independent results over shared evidence; it is not a choice or ranking contract. The Skill includes optional recipes across coding, debugging observations, test/report consistency, requirements, BAU status, documents and individual checklist items.

A recipe must preserve the claim's meaning. A trace containing a failure does not establish its cause. A test for one acceptance criterion does not establish complete coverage. A supported prerequisite is not permission to deploy. Arithmetic, dates and set completeness belong in deterministic tools.

## Primary purpose: narrow the judgement scope

LDF is an independent implementation inspired by [Jev](https://docs.typesafe.ai/)
and its separation of context from judgement questions. The aim is to quickly
narrow a factual judgement: what the supplied evidence establishes, what it rules
out, and what remains open. The caller can then focus evidence collection or the
next task decision. Token savings are a secondary effect, not the main criterion.

A supported answer can confirm a direction without changing the action. A
well-scoped abstention can identify the evidence needed next. Neither a verdict
reversal nor an action change is required for useful narrowing. Record observed
narrowing and, when naturally available, time to that narrowing and review effort;
do not infer usefulness from output length, token counts or success status alone.

## Feedback during normal work

At the existing task wrap-up, record a useful scope narrowing, source-reviewed
correction, confirmed unnecessary abstention, action change or newly known outcome.
Update the same case when more becomes known. This does not require a log for
every call, a new pilot, scheduled follow-ups or another model review.


For a separately chosen, small, time-bounded voluntary pilot on work already underway, keep selected skipped opportunities as well as calls. Do not log every routine step or force calls each turn. Check uncertain individual items and retain access to the underlying sources.

The empty `examples/usage-review.template.json` is a manual sidecar, not a new telemetry API or training example. Copy it into private local storage, set `template_only=false`, and fill only known facts:

- `participation`: `used`, `eligible_not_used`, or `not_eligible`.
- `receipt_id`: a real claim-check receipt, or null when no call occurred.
- `scenario`, `decision_question`, `criteria`, and `options_considered`: describe the actual decision.
- `notes` and existing evidence references: record what was uncertain, what was settled or ruled out, and what evidence or next step remains. Do not add a new telemetry field or reconstruct a missing packet from hashes.
- `unaided_action_before_check`: a contemporaneous baseline, not reconstructed after seeing the answer. Leave it null if no such record exists; leave `utility.action_changed` unknown without a recorded before/after comparison.
- `review`: source-based assessment, with `kind=human` only for actual human review. Expected answers remain unknown until reviewed.
- `recommendation_accepted`, `action_taken`, and `outcome`: separate observations; unknown outcomes stay unknown.
- `utility`: perceived help or estimated time saved is subjective without an adequate comparison. Changed action alone does not establish benefit.

Keep task/evidence/outcome records local and outside Git. Review false support, false contradiction, unnecessary abstention, invalid output and service failures separately by scenario. Consider latency, review burden and skipped opportunities. Capture and replay help reproduce failures but do not validate reference labels.

## Review correctness and track findings

Assess an expected verdict against the original claim, supplied evidence and
scope. An unnecessary abstention means that original packet already supported a
decisive answer. If new evidence was needed, an earlier `insufficient_evidence`
can be correct. Record the new evidence and receipt as progress rather than an
error. If the original packet is unavailable, leave its correctness unreviewed.
A matching replay or another model's agreement is not independent ground truth.

For a defensible expected verdict, use the documented CLI:

```sh
ldf feedback add RECEIPT_ID EXPECTED --kind agent-test --reason 'SOURCE_REF: short review reason'
ldf issue show ISSUE_ID
```

`EXPECTED` is `supported`, `contradicted`, or `insufficient_evidence`; `human`
is reserved for actual human review. If no expected verdict is established,
keep a utility or service-failure observation in the sidecar rather than inventing
a label. Each successful add creates a new issue; retain its ID and inspect the
existing finding, or `ldf issue list`, before adding the same finding again.
Action/outcome updates stay in the sidecar. Documented issue transitions track
actual fixes: `fixed` needs a reference and `regression_tested` needs a successful
matching child replay. New evidence alone does not establish a fix or regression
pass for the original packet. See [issue lifecycle](observability-replay.md#feedback-and-issue-lifecycle).

When reporting quality or utility, state the reviewed numerator/denominator,
scenario and selection method. Event-selected findings diagnose failure modes;
they do not estimate an error rate across all calls. In a chosen review sample,
include supported/no-change cases and skipped opportunities as well as failures.
Keep execution reliability, verdict correctness, useful narrowing, review effort
and observed outcome separate. Record only measured effort; unknowns stay unknown.

Use only task-authorized sources and writes. On read-only tasks, report the
observation with source/receipt references in chat without creating a sidecar.
Keep task records local and out of Git. These instructions do not authorize
capture, broader private-source access, schedules or extra reviewer calls.

## Separate future contracts

Choice and routing are experimental design directions, not implemented capabilities of `ldf_check_claim`. They must not be disguised as factual verdicts merely to reuse current scores or feedback labels.

A **choice** contract would take a task, explicit criterion, bounded evidence and offered options. It would return an offered option ID with citations, or abstain for ties/missing evidence. Selection would not execute or authorize the action.

A **routing** contract would take one item, explicit category definitions and evidence. It would return an offered category ID, or abstain for mixed work, overlapping categories or missing information. Classification would not assign, send or schedule work.

A future pilot needs its own runner, schema, reviewed cases and metrics. Freeze inputs before calls, vary option order, include abstentions, and use new immutable run directories. No training/evaluation cases or conversation-derived material are distributed in this public repository.
