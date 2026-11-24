Paths in commands are relative to the skill package root unless stated otherwise.

## Check modes

### Necessary mode (default)

Call LDF only when direct checks leave a consequential factual premise uncertain and the verdict can change or focus the next step. Skip verified facts, arithmetic, routine operations, and unchanged successful checks. Call frequency alone does not justify a check.

### Development mode (explicit opt-in)

Apply mandatory checkpoint rules only when a device's local config (for example `machine.md`) explicitly selects `development` mode to collect evaluation evidence:

- Call the claim-check tool (`ldf_check_claim`, CLI fallback when MCP is unavailable) and inspect the result before the next dependent action or reporting a conclusion across investigation, debugging, implementation, review, and BAU; routine evidence gathering and mechanical steps need no call.
- Prompt-level only, no hooks; reuse a verdict only when claim, evidence, and scope are unchanged.
- Supply one exact claim plus short verbatim evidence with unique IDs and valid source labels (`repo:`, `sheet:`, `email:`, or safe HTTP(S) URLs); never ask LDF for preferences or permission.
- Only `status=judged` counts: `supported` is not independent proof, `contradicted` requires source review, and `insufficient_evidence` leaves the premise open.
- A rejected, unavailable, or invalid result fails the checkpoint: fix the input or use the fallback; if still blocked, report it and continue only independent work unless the user waives it. Never bypass silently or switch models/providers silently.
- Pass `caller_request_id` (e.g. `alma://thread/<id>`) and a short `client` label (e.g. `alma`, `dsh`, `codex`) when `JEV_CLIENT_NAME` / client env is unset. Retain receipt IDs, separate rejected attempts from judged calls, and record wrap-up observations under [feedback](feedback.md).
