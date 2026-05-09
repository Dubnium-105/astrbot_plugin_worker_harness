"""AstrBot plugin entrypoint for astrbot_plugin_worker_harness."""

from __future__ import annotations

import re

from .audit_log import AuditLog
from .mcp_client import MCPClient, MCPError
from .policy import WorkerPolicy
from .router import TaskCategory, route_task
from .worker_prompts import build_worker_prompt

try:
    from astrbot.api.event import AstrMessageEvent, filter
    from astrbot.api.star import Context, Star, register
except ImportError:
    AstrMessageEvent = object
    Context = object
    Star = object

    class _FilterFallback:
        @staticmethod
        def command(*_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    def register(*_args, **_kwargs):
        def decorator(cls):
            return cls

        return decorator

    filter = _FilterFallback()


# Keywords for intent detection
_LIST_KEYWORDS = ("查看", "列出", "看", "list", "ls", "dir", "目录", "文件列表")
_READ_KEYWORDS = ("读", "读取", "read", "cat", "内容", "查看内容")
_WRITE_KEYWORDS = ("写", "写入", "write", "创建", "修改")


def _parse_task(task: str) -> dict:
    """Extract project_name, path, and intent from a natural-language task."""
    result: dict = {"project_name": ".", "relative_path": ".", "intent": "list"}

    # Detect intent
    lowered = task.lower()
    if any(kw in lowered for kw in _WRITE_KEYWORDS):
        result["intent"] = "write"
    elif any(kw in lowered for kw in _READ_KEYWORDS):
        result["intent"] = "read"
    elif any(kw in lowered for kw in _LIST_KEYWORDS):
        result["intent"] = "list"

    # Try to extract a project name from known subdirs or task text
    # Pattern: alphanumeric + underscore names that look like project names
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-]*", task)
    known = {"host_mcp_server", "astrbot_plugin_worker_harness", "tests",
             "prompts", "mcp", "qqbot"}
    for w in words:
        if w in known:
            result["project_name"] = w
            break

    # Extract relative path: anything that looks like a file path
    path_match = re.search(r"[a-zA-Z0-9_\-/]+\.[a-zA-Z]{1,6}", task)
    if path_match:
        p = path_match.group().lstrip("/")
        if not p.startswith(".."):
            # Split into project dir + file path
            parts = p.split("/", 1)
            if parts[0] in known:
                result["project_name"] = parts[0]
                result["relative_path"] = parts[1] if len(parts) > 1 else p
            else:
                result["relative_path"] = p

    return result


@register(
    "astrbot_plugin_worker_harness",
    "worker-harness",
    "Safe Worker Harness for A.S.T.R.A.",
    "0.1.0",
)
class WorkerHarnessPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None) -> None:
        super().__init__(context)
        self.config = config or {}
        self.policy = WorkerPolicy.from_config(self.config)
        self.audit_log = AuditLog()

    def _mcp_execute(self, intent: str, project: str, path: str) -> str:
        """Execute an MCP tool call and return the result as a string."""
        url = self.config.get("host_mcp_url", "http://172.18.0.1:8001")
        client = MCPClient(url, timeout=float(self.config.get("tool_call_timeout", 10)))

        if intent == "list":
            result = client.call("list_project_files", {
                "project_name": project, "relative_path": path,
            })
            files = result["content"][0]["text"]
            return f"文件列表 ({project}/{path}):\n{files}"

        elif intent == "read":
            result = client.call("read_project_file", {
                "project_name": project, "relative_path": path,
            })
            text = result["content"][0]["text"]
            return f"文件内容 ({project}/{path}):\n{text}"

        else:
            return f"不支持的操作: {intent}"

    @filter.command("worker")
    async def worker(self, event: AstrMessageEvent) -> None:
        raw = getattr(event, "message_str", "") or ""
        task = raw.removeprefix("/worker").strip() or "health check"
        route = route_task(task)

        # --- try execution path when host_mcp is allowed ---
        executed = False
        if (
            route.category == TaskCategory.HOST_MCP
            and self.policy.allow_host_mcp
            and self.config.get("host_mcp_url")
        ):
            try:
                parsed = _parse_task(task)
                result_text = self._mcp_execute(
                    intent=parsed["intent"],
                    project=parsed["project_name"],
                    path=parsed["relative_path"],
                )
                yield event.plain_result(result_text)
                executed = True
            except MCPError as exc:
                yield event.plain_result(
                    f"MCP 执行失败: {exc}\n\n路由: {route.category.value} / {route.action.value}"
                )
                executed = True
            except Exception:
                pass  # fall through to routing-only response

        if not executed:
            worker_prompt = build_worker_prompt(
                user_request=task,
                route=route,
                policy=self.policy,
                max_steps=int(self.config.get("max_steps", 8)),
            )
            self.audit_log.record(
                "worker.route",
                task=task,
                category=route.category.value,
                action=route.action.value,
                reason=route.reason,
                worker_prompt=worker_prompt,
            )
            yield event.plain_result(
                f"Worker Harness: {route.category.value} / {route.action.value}\n"
                f"{route.reason}"
            )
