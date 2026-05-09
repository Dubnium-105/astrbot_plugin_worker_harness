"""Task classification and routing decisions for the Worker Harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskCategory(str, Enum):
    ASTRBOT_PLUGIN = "astrbot_plugin"
    HOST_MCP = "host_mcp"
    SANDBOX = "sandbox"
    HIGH_RISK = "high_risk"


class RouteAction(str, Enum):
    ROUTE_TO_HARNESS = "route_to_harness"
    NEEDS_USER_CONFIRMATION = "needs_user_confirmation"


@dataclass(frozen=True)
class TaskRoute:
    category: TaskCategory
    action: RouteAction
    reason: str

    @property
    def needs_confirmation(self) -> bool:
        return self.action == RouteAction.NEEDS_USER_CONFIRMATION


HIGH_RISK_KEYWORDS = (
    "delete",
    "remove",
    "rm ",
    "shell",
    "exec",
    "sudo",
    "install",
    "token",
    "cookie",
    "secret",
    "password",
    ".env",
    "astrbot/core",
    "astrbot/api",
    "astrbot/platform",
    "config",
    "data/config",
)

HOST_MCP_KEYWORDS = (
    "host mcp",
    "host_mcp",
    "mcp server",
    "宿主机",
    "主机",
)

ASTRBOT_PLUGIN_KEYWORDS = (
    "astrbot plugin",
    "astrbot_plugin",
    "插件",
    "harness",
)


def classify_task(task: str) -> TaskCategory:
    normalized = _normalize_text(task)
    if not normalized:
        return TaskCategory.SANDBOX
    if _contains_any(normalized, HIGH_RISK_KEYWORDS):
        return TaskCategory.HIGH_RISK
    if _contains_any(normalized, HOST_MCP_KEYWORDS):
        return TaskCategory.HOST_MCP
    if _contains_any(normalized, ASTRBOT_PLUGIN_KEYWORDS):
        return TaskCategory.ASTRBOT_PLUGIN
    return TaskCategory.SANDBOX


def route_task(task: str) -> TaskRoute:
    category = classify_task(task)
    if category == TaskCategory.HIGH_RISK:
        return TaskRoute(
            category=category,
            action=RouteAction.NEEDS_USER_CONFIRMATION,
            reason="high-risk task needs user confirmation and was not executed",
        )
    if category == TaskCategory.HOST_MCP:
        return TaskRoute(
            category=category,
            action=RouteAction.NEEDS_USER_CONFIRMATION,
            reason="host MCP is disabled by default and needs user confirmation",
        )
    return TaskRoute(
        category=category,
        action=RouteAction.ROUTE_TO_HARNESS,
        reason="task can be handled by the Harness",
    )


def _normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\\", "/").lower().split())


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)
