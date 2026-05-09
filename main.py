"""AstrBot plugin entrypoint for astrbot_plugin_worker_harness."""

from __future__ import annotations

from .audit_log import AuditLog
from .policy import WorkerPolicy
from .router import route_task
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

    @filter.command("worker")
    async def worker(self, event: AstrMessageEvent, *args) -> None:
        task = " ".join(str(arg) for arg in args).strip() or "health check"
        route = route_task(task)
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
