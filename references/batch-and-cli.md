Paths in commands are relative to the skill package root unless stated otherwise.

## Several claims against shared evidence

`ldf_check_claims` (CLI: `ldf judge-claims`) accepts 1–8 unique `{id, claim}` items
and at most 12 shared evidence blocks. It returns `status=battery` and ordered
per-claim results, not one verdict for the batch. Inspect every result: uncached
entries carry their own status; cached entries currently omit status and may
lack the original citations/rationale. Provider failures are per claim.

Cache matching includes the claim, evidence, flow, caller request ID and client,
not the model/settings or age. There is no TTL. Use `ldf_check_claim` / `ldf judge`
when a fresh cited verdict is required. See the [batch/cache contract](../docs/observability-replay.md#batch-results-and-cache).

## CLI fallback

Send JSON on stdin rather than interpolating evidence into a shell command:

```python
import json, subprocess
packet = {
    "claim": "The supplied results support the report's zero-error claim.",
    "evidence": [{"id": "run:errors", "text": "Requests: 42646; failed requests: 1."}],
    "flow": "direct",
    "request_id": "alma://thread/<originating-thread-id>",
    "client": "alma"
}
r = subprocess.run(["/absolute/path/to/ldf", "judge"],
                   input=json.dumps(packet), text=True, capture_output=True, check=True)
result = json.loads(r.stdout)
print(result)  # Also inspect result["status"]; exit 0 alone does not mean judged.
```

Handled rejected/unavailable results also exit 0. A zero process exit code is
not a semantic verdict; see [README.md](../README.md#check-a-claim).
