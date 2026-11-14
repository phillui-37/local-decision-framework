Paths in commands are relative to the skill package root unless stated otherwise.

## Learn from real use

At existing task wrap-up, record a useful scope narrowing, source-reviewed
correction, confirmed unnecessary abstention, action change or newly known
outcome when observed. Update the same case rather than logging every call or
starting extra review work. Use `examples/usage-review.template.json` in private
local task records, outside Git, and leave unknown fields unknown:

- Keep the receipt and original evidence references. Use `decision_question` and
  `notes` for what was uncertain, what the check settled or ruled out, and the
  remaining evidence or next step. A skill-only install may lack the template;
  locate it in the source package rather than installing a runtime to record notes.
- Judge correctness against the original supplied evidence. New evidence can
  justify a changed verdict without making an earlier abstention an error.
- Record a pre-check action only from contemporaneous records; do not invent a
  baseline afterward. Keep actual action, observed outcome, review effort and
  perceived benefit separate. No action change does not imply no useful narrowing.

For a reviewed expected verdict, use
`ldf feedback add ID EXPECTED --kind agent-test --reason TEXT`; `human` is only
for actual human review. Each add creates a new issue: retain its ID, check for
an existing finding, and use documented `issue` transitions for actual fixes.
Without a defensible expected verdict, leave the observation in the sidecar.
`regression_tested` requires a successful matching child replay; a fresh check
with new evidence is not proof of a fix. Do not use LDF self-ratings as ground truth.

See [feedback during normal work](../docs/scenario-pilot.md#feedback-during-normal-work)
for field guidance and reporting limits. Report selected-case denominators and
selection methods; execution success, useful narrowing and token usage are
separate metrics. Read-only tasks keep observations in chat without writing.

For explicitly authorized debugging/regression work, MCP `capture=true` or `ldf judge --capture` stores input privately. Raw responses additionally require `LDF_CAPTURE_RESPONSE=1`; both are off by default. `ldf replay ID --mode original --expected LABEL` is offline; `--mode current` makes a new configured-model call. Hashes cannot reconstruct missing captures. Do not silently capture sensitive evidence or change the configured provider.
