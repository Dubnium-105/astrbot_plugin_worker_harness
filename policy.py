"""Safety policy for astrbot_plugin_worker_harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_PROTECTED_ROOTS = (
    "astrbot",
    "AstrBot",
    "astrbot/core",
    "astrbot/api",
    "astrbot/platform",
    "config",
    "data/config",
)

SENSITIVE_PATH_MARKERS = (
    ".env",
    "token",
    "cookie",
    "secret",
    "password",
)


class PolicyViolation(PermissionError):
    """Raised when a tool request violates the Worker Harness policy."""


@dataclass(frozen=True)
class WorkerPolicy:
    protected_roots: tuple[str, ...] = DEFAULT_PROTECTED_ROOTS
    allowed_write_roots: tuple[str, ...] = field(default_factory=tuple)
    allow_shell: bool = False
    allow_host_mcp: bool = False

    @classmethod
    def from_config(cls, config: dict | None) -> "WorkerPolicy":
        config = config or {}
        return cls(
            protected_roots=tuple(
                config.get("protected_roots") or DEFAULT_PROTECTED_ROOTS
            ),
            allowed_write_roots=tuple(config.get("allowed_write_roots") or ()),
            allow_shell=bool(config.get("allow_shell", False)),
            allow_host_mcp=bool(config.get("allow_host_mcp", False)),
        )

    def assert_read_allowed(self, path: str | Path) -> None:
        normalized = _normalize_path(path)
        if _contains_sensitive_marker(normalized):
            raise PolicyViolation("reading sensitive paths is not allowed")

    def assert_write_allowed(self, path: str | Path) -> None:
        normalized = _normalize_path(path)
        if _contains_sensitive_marker(normalized):
            raise PolicyViolation("writing sensitive paths is not allowed")
        if _is_under_any(normalized, self.protected_roots):
            raise PolicyViolation("writing protected AstrBot paths is not allowed")
        if not self.allowed_write_roots:
            raise PolicyViolation("no write roots are configured")
        if not _is_under_any(normalized, self.allowed_write_roots):
            raise PolicyViolation("path is outside allowed write roots")

    def assert_shell_allowed(self, command: str | None = None) -> None:
        if not self.allow_shell:
            raise PolicyViolation("shell access is disabled by default")
        if not command or not command.strip():
            raise PolicyViolation("shell command is required")

    def assert_host_mcp_allowed(self, server_name: str | None = None) -> None:
        if not self.allow_host_mcp:
            raise PolicyViolation("host MCP access is disabled by default")
        if not server_name or not server_name.strip():
            raise PolicyViolation("host MCP server name is required")


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip().strip("/")


def _contains_sensitive_marker(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in SENSITIVE_PATH_MARKERS)


def _is_under_any(path: str, roots: tuple[str, ...]) -> bool:
    normalized_roots = tuple(_normalize_path(root) for root in roots)
    return any(path == root or path.startswith(f"{root}/") for root in normalized_roots)
