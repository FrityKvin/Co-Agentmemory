# Co-Agentmemory Universal Guide

Use this guide when the target client does not support native Skill packages.

The system has two layers:

1. AgentMemory for concise, searchable machine memory.
2. Obsidian for human-readable project and life records.

Use three write tiers:

- Memory: durable state, decisions, pointers, and handoffs go to both layers.
- Project: detailed plans and reports stay in the relevant Obsidian project directory.
- Routine: dated operational logs go to Obsidian and AgentMemory.

Configure `CO_MEMORY_VAULT_ROOT`, `AGENTMEMORY_URL`, `AGENTMEMORY_SECRET`,
`CO_MEMORY_ACTOR_ID`, and `CO_MEMORY_TIMEZONE` in the runtime. Read
`references/configuration.md` for profile-based configuration.

Use `scripts/write_log.py` and `scripts/write_handoff.py` for durable writes.
Read `Agent_Comemory/00_Index/` and `Agent_Comemory/01_Shared/` at session start,
then retrieve only relevant memory slots and project context.

The recommended personal Daily path is
`Personal_Wiki/01_Daily/YYYY/YYYY-MM-DD.md`. The recommended agent log path is
`Agent_Comemory/03_Logs/YYYY/YYYY-MM/YYYY-MM-DD.md`. Keep those streams separate.

Never write credentials to shared memory or Markdown. If AgentMemory is
unreachable, preserve the outbox and run `python3 scripts/doctor.py --flush-outbox`
after connectivity returns.

