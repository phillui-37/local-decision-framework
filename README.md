# Local Decision Framework

Evidence-grounded claim checks for coding agents and everyday operational work, through a shared Python core, CLI, and MCP server.

**Inspired by [Jev](https://docs.typesafe.ai/)** and its separation of context from judgement questions. This is an independent prototype; it does not require the TypeSafe API or claim equivalent model quality or wire compatibility.

## What it does

Give it one factual claim and a small evidence packet. It returns a cited verdict:

- `supported`
- `contradicted`
- `insufficient_evidence`

Operational failures and invalid model responses are separate from semantic verdicts. The tool cannot inspect files independently, prove causality or complete coverage, grant permission, or decide that an action is safe to execute.

Use it selectively for code/diff facts, debugging observations, requirement/report consistency, BAU status, document checks, and individual checklist items. Skip obvious facts, arithmetic, and checks already resolved by direct verification.

## Install

Requires Python 3.10+ and an OpenAI-compatible model endpoint.

```bash
git clone https://github.com/phillui-37/local-decision-framework.git
cd local-decision-framework
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Or use `uv`:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

The package installs `ldf` and `ldf-mcp`, exposes the MCP tool `ldf_check_claim`, and uses `LDF_*` settings with data under `~/.local/share/ldf`. For backward compatibility with existing integrations, the legacy `jev` / `jev-mcp` commands, the `jev` Python namespace, `JEV_*` environment variables (silently respected), and an existing `~/.local/share/jev` data directory continue to work. "Jev" in this repository refers only to this legacy naming and to the TypeSafe project credited above; this tool is unrelated to any hosted Jev service.

## Configure a model

No endpoint or model is selected automatically. Set them explicitly:

```bash
export LDF_BASE_URL=http://127.0.0.1:8000/v1
export LDF_MODEL=your-local-model
export LDF_OUTPUT_MODE=json_schema
# Optional authentication; do not put credentials in source or MCP arguments.
export LDF_API_KEY_FILE="$HOME/.config/your-runtime/api-key"

.venv/bin/ldf doctor --probe
```

`LDF_BASE_URL` includes `/v1`. A remote endpoint is also supported when you choose it explicitly; evidence will then be sent to that provider. There is no automatic model, provider, or output-format fallback.

| Setting | Purpose |
|---|---|
| `LDF_BASE_URL`, `LDF_MODEL` | Required endpoint and model ID |
| `LDF_API_KEY_FILE` or `LDF_API_KEY` | Optional provider authentication |
| `LDF_OUTPUT_MODE` | `json_schema`, `json_object` (default), or `plain` |
| `LDF_TIMEOUT` | Per-call timeout, 1–300 seconds; default 30 |
| `LDF_MAX_OUTPUT_TOKENS` | Output budget, 1–8192; default 1200 |
| `LDF_REASONING_EFFORT` | Optional provider-specific setting |
| `LDF_DATA_DIR` | Private receipt/capture storage; default `~/.local/share/ldf` (falls back to a legacy `~/.local/share/jev` if present) |

Every `LDF_*` setting also accepts its legacy `JEV_*` spelling, so existing configurations keep working unchanged.

Use a mode supported by your backend. Schema-constrained output still passes local strict validation; JSON validity and valid citations do not establish judgement correctness.

## Check a claim

```bash
printf '%s\n' '{
  "claim": "The supplied run recorded no failures.",
  "evidence": [
    {"id": "run", "text": "Requests: 1000; failed requests: 2."}
  ],
  "flow": "direct"
}' | .venv/bin/ldf judge
```

Evidence blocks have a unique `id`, nonblank `text`, and optional `scope` and `source`. Locators are labels, not resources the tool fetches. Flows are `direct` and `evidence-first`.

Only `status=judged` carries a usable verdict. `unavailable`, `invalid_model_output`, and `rejected` provide no verdict. Review consequential conclusions against their sources.

## MCP and Skills

Register this stdio server in your client, replacing the paths and model settings:

```json
{
  "mcpServers": {
    "local-decision-framework": {
      "command": "/absolute/path/to/local-decision-framework/.venv/bin/ldf-mcp",
      "args": [],
      "env": {
        "LDF_BASE_URL": "http://127.0.0.1:8000/v1",
        "LDF_MODEL": "your-local-model",
        "LDF_OUTPUT_MODE": "json_schema"
      }
    }
  }
}
```

The server exposes three tools: `ldf_check_claim`, `ldf_summarize_output`, and `ldf_fetch_evidence`. Client-qualified names may vary. For existing integrations, the legacy `jev-mcp` command launches the same server.

[SKILL.md](SKILL.md) teaches when to call it across coding and BAU tasks, how to prepare bounded evidence, and when to abstain. Install it through your agent's Skill mechanism and set its CLI fallback path for your machine. Invocation stays optional and advisory.

## Receipts, replay and feedback

Receipts contain timing, versions, model/settings fingerprints, input hashes and safe response diagnostics. Inputs and raw responses are not retained by default.

```bash
# Explicitly capture this debugging request and its raw response locally.
LDF_CAPTURE_RESPONSE=1 .venv/bin/ldf judge --capture < packet.json

.venv/bin/ldf receipts show RECEIPT_ID
.venv/bin/ldf replay RECEIPT_ID --mode original --expected contradicted
.venv/bin/ldf replay RECEIPT_ID --mode current --expected contradicted

.venv/bin/ldf feedback add RECEIPT_ID contradicted \
  --kind human --reason "Checked against the original result."
.venv/bin/ldf issue list
```

Original replay checks the saved response offline. Current replay makes a new configured-model call and links its receipt to the original. Missing inputs cannot be recovered from a hash. Agent-test feedback is distinct from actual human review; a successful replay is required before an issue can be marked regression-tested.

See [observability and replay](docs/observability-replay.md) and [wider scenario usage](docs/scenario-pilot.md). The [empty usage-review template](examples/usage-review.template.json) can hold manual observations alongside a receipt.

## Development

The tests use synthetic unit-test mocks and local HTTP servers; they require no live model or credentials.

```bash
.venv/bin/python -m pip install -e .
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

This public repository contains framework code, unit tests, usage documentation, and the distributable Skill. Training/evaluation datasets, benchmark recordings, real request data, captures, receipts, agent conversation records, and private research history are excluded from Git and distribution artifacts.

## Prototype limits

This is an experimental decision aid. Model and scenario quality must be evaluated separately from protocol validity and replay reproducibility. Choice, routing, ranking, automatic runtime hooks, cross-model consensus, and compatibility with the hosted Jev protocol are not implemented. No general accuracy, calibrated-confidence, or autonomy claim is made.

## Deterministic output evidence

Register test/build/log output with `ldf source register <path>` (or `-` for stdin), inspect it using `ldf source summarize <ref_id>`, then retrieve numbered details with `ldf source fetch <ref_id> --lines N:M` or `--errors first=K|all`. Summaries name their detection scope and separate source-wide counts from displayed events; they never prove absence. Hash changes are reported as `stale_source`. See [docs/evidence-layer.md](docs/evidence-layer.md).
