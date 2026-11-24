Paths in commands are relative to the skill package root unless stated otherwise.

## Runtime prerequisites — check before use

This skill is instructions, not the runtime itself. Use the owner's `local-decision-framework` repository ([source](https://github.com/phillui-37/local-decision-framework)). Require Python **3.10+** and the project's dependencies from `pyproject.toml` (`mcp>=1.30,<2`; see the current package version there).

First discover an available MCP tool or an installed `ldf` CLI. Do not reinstall a working runtime. If neither is available, locate the source checkout and verify Python. Obtain the user's confirmation before installing Python or project dependencies. Run the following from that checkout; create `.venv` only if no suitable environment exists. Never copy a Mac `.venv` to Windows.

Windows (PowerShell):

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\ldf.exe --help
```

macOS / Linux:

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/ldf --help
```

Use the verified absolute CLI path for the fallback below. For MCP, register the absolute path to `.venv/Scripts/ldf-mcp.exe` on Windows or `.venv/bin/ldf-mcp` on macOS/Linux, with that device's intended gateway/model settings. Do not reuse a Mac hostname-gated MCP entry on Windows. Reconnect the client and confirm `ldf_check_claim` is exposed; `--help` alone verifies CLI startup, not MCP registration or model connectivity.

### Windows per-device environment hydration

Provider/model settings are per-device, and an already-running Windows client can inherit stale environment variables. Before probing or judging in a PowerShell 7 shell (without changing Execution Policy), fill only unset process variables from the device's saved Windows User environment:

```powershell
foreach ($LdfSetting in @('LDF_BASE_URL', 'LDF_MODEL', 'LDF_MAX_OUTPUT_TOKENS', 'LDF_OUTPUT_MODE', 'LDF_TIMEOUT')) {
    if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($LdfSetting, 'Process'))) {
        $LdfSavedValue = [Environment]::GetEnvironmentVariable($LdfSetting, 'User')
        if (-not [string]::IsNullOrEmpty($LdfSavedValue)) {
            [Environment]::SetEnvironmentVariable($LdfSetting, $LdfSavedValue, 'Process')
        }
    }
}
$Ldf = Join-Path $env:USERPROFILE '.agents\skills\ldf-check-claim\.venv\Scripts\ldf.exe'
# Invoke only after confirming this executable exists and starts.
& $Ldf doctor --probe
```

This does not invent a provider/model or override an explicit process setting.

If installation, registration, or a check fails, report the exact missing prerequisite and stop the check-dependent step. Continue independent work where allowed; never treat a missing runtime as a successful check or claim it was never installed based only on a missing path.
