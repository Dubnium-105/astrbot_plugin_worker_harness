"""Minimal MCP SSE client (stdlib only) for the Worker Harness.

Usage:
    client = MCPClient("http://host:8001")
    result = client.call("list_project_files", {"project_name": "foo"})
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any


class MCPError(Exception):
    """Raised when an MCP call fails."""


class MCPClient:
    """One-shot MCP SSE client. Connects, handshakes, calls one tool, closes."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session_id: str | None = None
        self._events: list[str] = []
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Full SSE handshake + single tool call. Returns the tool result."""
        self._connect()
        self._initialize()
        return self._call_tool(tool_name, arguments)

    # -- connect + handshake ------------------------------------------------

    def _connect(self) -> None:
        self._events.clear()
        self._sse_done = threading.Event()

        def _read() -> None:
            try:
                req = urllib.request.Request(f"{self.base_url}/sse")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    for line_bytes in resp:
                        with self._lock:
                            self._events.append(line_bytes.decode("utf-8").strip())
                        if sum(1 for e in self._events if e.startswith("data:")) > 10:
                            break
            except Exception:
                pass
            finally:
                self._sse_done.set()

        self._sse_thread = threading.Thread(target=_read, daemon=True)
        self._sse_thread.start()

        deadline = time.time() + 5.0
        while time.time() < deadline:
            with self._lock:
                for line in self._events:
                    if "sessionId=" in line:
                        self._session_id = line.split("sessionId=")[1].strip()
                        return
            time.sleep(0.05)
        raise MCPError("timeout waiting for SSE session")

    def _initialize(self) -> None:
        resp = self._rpc({"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}, "id": 1})
        if "error" in resp:
            raise MCPError(f"initialize: {resp['error']}")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        result = self._rpc({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": name, "arguments": args}, "id": 200})
        inner = result.get("result", {})
        if inner.get("isError"):
            raise MCPError(inner.get("content", [{}])[0].get("text", "tool error"))
        return inner

    # -- low-level I/O -----------------------------------------------------

    def _rpc(self, msg: dict[str, Any], deadline: float = 8.0) -> dict[str, Any]:
        with self._lock:
            self._events.clear()
        self._post(msg)

        msg_id = msg["id"]
        dl = time.time() + deadline
        while time.time() < dl:
            with self._lock:
                for line in self._events:
                    if f'"id": {msg_id}' in line and line.startswith("data:"):
                        return json.loads(line.split("data:", 1)[1].strip())
            time.sleep(0.05)
        raise MCPError(f"timeout waiting for id={msg_id}")

    def _post(self, msg: dict[str, Any]) -> None:
        url = f"{self.base_url}/messages?sessionId={self._session_id}"
        data = json.dumps(msg).encode("utf-8")
        try:
            urllib.request.urlopen(
                urllib.request.Request(url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"),
                timeout=self.timeout,
            )
        except urllib.error.URLError as exc:
            raise MCPError(f"POST failed: {exc}") from exc
