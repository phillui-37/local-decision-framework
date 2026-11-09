# Wider usage without stretching the contract

Local Decision Framework exposes single-claim and batch claim-check tools. A batch
returns independent results over shared evidence; it is not a choice or ranking contract. The Skill includes optional recipes across coding, debugging observations, test/report consistency, requirements, BAU status, documents and individual checklist items.

A recipe must preserve the claim's meaning. A trace containing a failure does not establish its cause. A test for one acceptance criterion does not establish complete coverage. A supported prerequisite is not permission to deploy. Arithmetic, dates and set completeness belong in deterministic tools.

## Observe useful decision points

Use a small, time-bounded voluntary pilot on work already underway. Keep selected skipped opportunities as well as calls; do not log every routine step or force calls each turn. Check uncertain individual items and retain access to the underlying sources.

The empty `examples/usage-review.template.json` is a manual sidecar, not a new telemetry API or training example. Copy it into private local storage, set `template_only=false`, and fill only known facts:

- `participation`: `used`, `eligible_not_used`, or `not_eligible`.
- `receipt_id`: a real claim-check receipt, or null when no call occurred.
- `scenario`, `decision_question`, `criteria`, and `options_considered`: describe the actual decision.
- `unaided_action_before_check`: a contemporaneous baseline, not reconstructed after seeing the answer.
- `review`: source-based assessment, with `kind=human` only for actual human review. Expected answers remain unknown until reviewed.
- `recommendation_accepted`, `action_taken`, and `outcome`: separate observations; unknown outcomes stay unknown.
- `utility`: perceived help or estimated time saved is subjective without an adequate comparison. Changed action alone does not establish benefit.

Keep task/evidence/outcome records local and outside Git. Review false support, false contradiction, unnecessary abstention, invalid output and service failures separately by scenario. Consider latency, review burden and skipped opportunities. Capture and replay help reproduce failures but do not validate reference labels.

## Separate future contracts

Choice and routing are experimental design directions, not implemented capabilities of `ldf_check_claim`. They must not be disguised as factual verdicts merely to reuse current scores or feedback labels.

A **choice** contract would take a task, explicit criterion, bounded evidence and offered options. It would return an offered option ID with citations, or abstain for ties/missing evidence. Selection would not execute or authorize the action.

A **routing** contract would take one item, explicit category definitions and evidence. It would return an offered category ID, or abstain for mixed work, overlapping categories or missing information. Classification would not assign, send or schedule work.

A future pilot needs its own runner, schema, reviewed cases and metrics. Freeze inputs before calls, vary option order, include abstentions, and use new immutable run directories. No training/evaluation cases or conversation-derived material are distributed in this public repository.
