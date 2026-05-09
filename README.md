# astrbot_plugin_worker_harness

Safe Worker Harness plugin skeleton for AstrBot.

## Scope

This version implements the AstrBot plugin Harness prompt assembly and safe
routing. It does not modify AstrBot core.

## Command

The plugin registers:

```text
/worker <task>
```

The command classifies the task and returns a Harness routing decision.
High-risk tasks return `needs_user_confirmation` and are not executed.

When the Harness prepares a Worker request, it assembles:

- Worker system prompt
- User original request
- Task classification
- Permission policy
- Output format

Prompt templates live in:

- `prompts/astra_frontend_prompt.txt`
- `prompts/worker_system_prompt.txt`
- `prompts/worker_task_template.txt`

Worker output must use these sections:

- `执行摘要`
- `完成情况`
- `关键结果`
- `问题与风险`
- `建议下一步`

## Task Categories

- `astrbot_plugin`
- `host_mcp`
- `sandbox`
- `high_risk`

## Security Defaults

- Shell is disabled by default.
- Host MCP is disabled by default.
- Writes are denied unless `allowed_write_roots` is configured.
- Writes to `astrbot/`, `AstrBot/`, `astrbot/core`, `astrbot/api`,
  `astrbot/platform`, `config`, and `data/config` are denied.
- Reads of sensitive paths containing `.env`, `token`, `cookie`, `secret`, or
  `password` are denied.

## Tests

From the repository root:

```bash
python3 -m unittest discover -s tests
```
