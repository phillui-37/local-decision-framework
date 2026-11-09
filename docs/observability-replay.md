# Receipts, replay and issues

Local Decision Framework keeps execution metadata by default. This supports tracing failures; it is not a CPU profiler or a model-quality guarantee.

## Storage and privacy

`LDF_DATA_DIR` selects a private local data directory, defaulting to the existing local data directory. `LDF_RECEIPTS_FILE`, `LDF_FEEDBACK_FILE`, and `LDF_CAPTURE_DIR` can override individual paths. Do not put runtime storage inside version-controlled source.

Receipts record status/verdict, timing, safe HTTP/validation diagnostics, configured/returned model IDs, settings, prompt/schema identities and source/input hashes. Unknown usage is null. Provider credentials and error bodies are not logged as diagnostics.

Input capture and response capture are separate opt-ins:

```bash
ldf judge --capture < packet.json
LDF_CAPTURE_RESPONSE=1 ldf judge --capture < packet.json
```

`LDF_CAPTURE=1` enables input capture for a deliberately configured debugging session. Captured inputs contain the supplied evidence, so enable this only in a trusted local data directory. Raw provider responses are bounded and marked when truncated. Capture files are created with private permissions. Source labels are not fetched.

## Inspect and replay

```bash
ldf receipts list
ldf receipts show RECEIPT_ID
ldf receipts export --format jsonl
ldf replay RECEIPT_ID --expected supported --mode original
ldf replay RECEIPT_ID --expected supported --mode current
```

Original replay verifies capture integrity and known prompt/schema versions, then validates the saved model response offline against the original offered evidence IDs. It requires a complete captured response. Unsupported versions, missing captures, or corrupted captures are explicit failures.

Current replay makes a new call through the current configured backend, creates a linked receipt, and reports whether source versions differ. Intact captured inputs can support current replay even when the old response was truncated. This does not reproduce historical model behaviour.

## Feedback and issue lifecycle

```bash
ldf feedback add RECEIPT_ID contradicted --kind human --reason "Checked the source."
ldf feedback list
ldf feedback export --format jsonl
ldf issue list
ldf issue show ISSUE_ID
ldf issue update ISSUE_ID confirmed --kind human --reason "Reproduced."
ldf issue update ISSUE_ID fixed --ref COMMIT_OR_FIX_REFERENCE
ldf issue update ISSUE_ID regression_tested --replay-receipt NEW_RECEIPT_ID
```

Feedback refers to an existing receipt and preserves its observed result. Provider/schema failures can be tracked without a semantic verdict. The default feedback kind is `agent-test`; use `human` only for actual human feedback.

Transitions are append-only. `fixed` requires an explicit reference; `regression_tested` requires a successful matching child replay of the issue's original request. A valid JSON response alone does not resolve a model-quality issue. Legacy receipt/feedback rows remain readable.

## Regression manifests

`ldf regression cases.json` accepts an explicit manifest containing `cases`. Each case has a unique `id`, `claim`, `evidence`, `expected` verdict, and `evidence_ids` from the offered evidence blocks. The complete manifest is validated before any model request. Capture is opt-in. The report separates provider failures, invalid outputs and semantic mismatches; repeated provider failures stop the run with an incomplete report.

Keep every experiment's manifest, model/settings, versions and result directory distinct. Do not replace completed historical artifacts or tune on held-out cases. This repository intentionally ships no training/evaluation corpus, recordings, model receipts or agent conversation archive.

## Output modes

Set `LDF_OUTPUT_MODE` to `json_schema`, `json_object`, or `plain`. There is no silent retry with another format/provider. A strict provider-facing schema constrains offered citation IDs and uses a portable decoder subset; local validation also rejects duplicate/unknown citations and decisive results without evidence. Some providers accept only a subset of JSON Schema.

Logging and replay establish traceability and reproducibility of recorded processing. Answer quality and decision usefulness still need review against appropriate task evidence.
