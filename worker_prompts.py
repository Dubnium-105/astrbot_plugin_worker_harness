"""Prompt assembly for A.S.T.R.A. and the Worker Agent."""

from __future__ import annotations

from pathlib import Path

from .policy import WorkerPolicy
from .router import TaskRoute, route_task


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

ASTRA_FRONTEND_PROMPT = (PROMPTS_DIR / "astra_frontend_prompt.txt").read_text(
    encoding="utf-8"
)
WORKER_SYSTEM_PROMPT = (PROMPTS_DIR / "worker_system_prompt.txt").read_text(
    encoding="utf-8"
)
WORKER_TASK_TEMPLATE = (PROMPTS_DIR / "worker_task_template.txt").read_text(
    encoding="utf-8"
)


def build_worker_prompt(
    user_request: str,
    route: TaskRoute | None = None,
    policy: WorkerPolicy | None = None,
    max_steps: int = 8,
) -> str:
    policy = policy or WorkerPolicy()
    route = route or route_task(user_request)
    return WORKER_TASK_TEMPLATE.format(
        worker_system_prompt=WORKER_SYSTEM_PROMPT.strip(),
        user_request=user_request.strip(),
        task_category=route.category.value,
        route_action=route.action.value,
        route_reason=route.reason,
        allow_shell=str(policy.allow_shell).lower(),
        allow_host_mcp=str(policy.allow_host_mcp).lower(),
        protected_roots=", ".join(policy.protected_roots) or "(none)",
        allowed_write_roots=", ".join(policy.allowed_write_roots) or "(none)",
        max_steps=max_steps,
    )
