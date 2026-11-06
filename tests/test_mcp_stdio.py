"""Regression for Windows Git stdin inheritance blocking MCP stdio replies."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows subprocess stdin regression")
class WindowsMcpStdioTests(unittest.TestCase):
    def test_git_stdin_inheritance_does_not_block_tool_response(self):
        root = Path(__file__).resolve().parents[1]

        async def exercise(env):
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "jev.mcp_server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=root, env=env,
            )

            async def send(message):
                process.stdin.write((json.dumps(message) + "\n").encode())
                await process.stdin.drain()

            async def receive(request_id):
                line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
                self.assertTrue(line, "MCP server exited before replying")
                response = json.loads(line)
                self.assertEqual(response["id"], request_id)
                self.assertIn("result", response)
                return response["result"]

            try:
                await send({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "git-stdin-regression", "version": "1"},
                    },
                })
                await receive(1)
                await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                await send({
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {
                        "name": "jev_check_claim",
                        "arguments": {"claim": "No evidence is available.", "evidence": []},
                    },
                })
                # Keep stdin open: closing it would hide the original deadlock.
                response = await receive(2)
                self.assertFalse(response.get("isError", False))
                payload = json.loads(response["content"][0]["text"])
                self.assertEqual(payload["status"], "judged")
                self.assertEqual(payload["verdict"], "insufficient_evidence")
                self.assertEqual(payload["persistence"], "recorded")
            finally:
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        process.kill()
                        await asyncio.wait_for(process.wait(), timeout=5)
                process.stdin.close()
                await process.stdin.wait_closed()

        with tempfile.TemporaryDirectory() as data_dir:
            env = dict(os.environ, PYTHONPATH=str(root / "src"), JEV_DATA_DIR=data_dir)
            asyncio.run(exercise(env))
            self.assertTrue((Path(data_dir) / "receipts.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
