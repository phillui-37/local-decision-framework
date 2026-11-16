# Receipts, replay and issues

Local Decision Framework keeps execution metadata by default. This supports tracing failures; it is not a CPU profiler or a model-quality guarantee.

## Storage and privacy

`LDF_DATA_DIR` selects a private local data directory, defaulting to the existing local data directory. `LDF_RECEIPTS_FILE`, `LDF_FEEDBACK_FILE`, and `LDF_CAPTURE_DIR` can override individual paths. Do not put runtime storage inside version-controlled source.

Receipts record status/verdict, timing, safe HTTP/validation diagnostics, configured/returned model IDs, settings, prompt/schema identities and source/input hashes. Judged batch claim receipts also record citation IDs and the model's rationale for cache reuse. Rationales can repeat sensitive evidence; protect receipt files accordingly. Unknown usage and unavailable package or Git provenance are null. Provider credentials and error bodies are not logged as diagnostics. Invalid packets reaching the core produce a minimal rejection receipt without input content. Malformed JSON or requests rejected before reaching the core are not receipted. Corrupt storage records cause an explicit error with their file and line number; repair the storage before continuing.

Input capture and response capture are separate opt-ins:

```bash
ldf judge --capture < packet.json
LDF_CAPTURE_RESPONSE=1 ldf judge --capture < packet.json
```

`LDF_CAPTURE=1` enables input capture for a deliberately configured debugging session. Captured inputs contain the supplied evidence, so enable this only in a trusted local data directory. Raw provider responses are bounded and marked when truncated. Capture files are created with private permissions. Source labels are not fetched.

## Batch results and cache

`ldf judge-claims` / `ldf_check_claims` accepts 1–8 claims and at most 12 shared
evidence blocks. It checks uncached claims sequentially through the single-claim
core. Invalid input rejects the batch before the loop; an operational failure
returned for a claim is recorded in that claim's result and processing continues.
The top-level `status=battery` does not assert that every claim was judged.

The response contains the batch `request_id`, `battery_hash`, `cached`, `cache_misses`, `http_attempts`, `persistence` and ordered `results`. Each item identifies the claim and source receipt and reports status, persistence and whether it was cached. Judged items include verdict, citations and rationale; failed items can carry an error code. A cached item references its original receipt. Fresh claim receipts link back to their batch and claim ID; the batch receipt lists all source receipt IDs, including cache hits. If a receipt write fails, completed results are still returned with `persistence=failed` at the affected level.

`cache_misses` counts claims passed to the judge; `http_attempts` counts requests started at the HTTP transport, including failed requests. The legacy `provider_calls` field in new batch receipts equals `http_attempts`; older receipts counted misses instead.

Cache matching hashes the normalized single-claim packet: claim text, shared
evidence (including order and supplied fields), flow, caller request ID and
resolved client. The batch's claim ID is not part of that per-claim key. Reuse
requires an exact input hash and a prior `status=judged` receipt with a complete result. Single-claim receipts do not normally contain that result and are not reused.

Cache entries expire after 86400 seconds (24 hours) by default. Set
`LDF_CACHE_TTL_SECONDS` to a nonnegative integer to change the lifetime; `0`
disables reuse. The legacy `JEV_CACHE_TTL_SECONDS` name also works. Invalid
values reject the batch with `invalid_cache_ttl`. A receipt is reusable only
when its timezone-aware ISO 8601 timestamp is not in the future and its age is
strictly less than the TTL. Missing, malformed, timezone-less and future
timestamps are cache misses; receipts remain in storage.

Current limits:

- There is no cache-clear command or model/prompt/settings-aware invalidation.
  Changing provider settings alone does not force a fresh batch verdict.
- Older receipts without citation IDs and rationale are not cache hits; the claim is judged again.
- Use `ldf judge` / `ldf_check_claim` for a fresh cited check; those paths do not
  use the batch cache. A deliberately separate `LDF_DATA_DIR` isolates a new
  experiment's history without deleting existing receipts.
- CLI input capture is available via `judge-claims --capture`; the batch MCP
  tool currently has no capture argument. A hit does not create a new model
  response or reconstruct missing captured input.

Review each item independently and retain source evidence. Do not treat a cached
verdict as a new observation under the current model configuration.

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
