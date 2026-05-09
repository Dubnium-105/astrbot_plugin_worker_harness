"""Safe tool wrappers used by the Worker Harness.

These wrappers are intentionally small. They enforce policy before touching the
filesystem or returning a tool decision. Shell and host MCP actions are not
executed in this first version.
"""

from __future__ import annotations

from pathlib import Path

from .policy import PolicyViolation, WorkerPolicy


class SafeFileTool:
    def __init__(self, policy: WorkerPolicy) -> None:
        self.policy = policy

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        self.policy.assert_read_allowed(path)
        return Path(path).read_text(encoding=encoding)

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> dict:
        self.policy.assert_write_allowed(path)
        Path(path).write_text(content, encoding=encoding)
        return {"status": "ok", "path": str(path)}


class SafeShellTool:
    def __init__(self, policy: WorkerPolicy) -> None:
        self.policy = policy

    def run(self, command: str) -> dict:
        try:
            self.policy.assert_shell_allowed(command)
        except PolicyViolation as exc:
            return {"status": "needs_user_confirmation", "reason": str(exc)}
        return {
            "status": "needs_user_confirmation",
            "reason": "shell execution is not implemented in Harness v1",
        }


class SafeMCPTool:
    def __init__(self, policy: WorkerPolicy) -> None:
        self.policy = policy

    def call(self, server_name: str, tool_name: str, arguments: dict | None = None) -> dict:
        try:
            self.policy.assert_host_mcp_allowed(server_name)
        except PolicyViolation as exc:
            return {"status": "needs_user_confirmation", "reason": str(exc)}
        return {
            "status": "needs_user_confirmation",
            "reason": "host MCP calls are not implemented in Harness v1",
            "server_name": server_name,
            "tool_name": tool_name,
            "arguments": arguments or {},
        }
