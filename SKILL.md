---
name: co-agentmemory
description: >-
  Join a vendor-neutral shared memory workflow using AgentMemory and Obsidian.
  Use for multi-agent onboarding, durable context, handoffs, project continuity,
  and memory governance across AI runtimes.
metadata:
  short-description: Share agent context through AgentMemory and Obsidian
---

# Co-Agentmemory

Use this Skill when an agent joins a shared AgentMemory + Obsidian workspace.
The system has two layers and three write tiers. Classify information before
writing so memory stays useful and project documents retain their detail.

## System Model

- **AgentMemory** is the machine-readable retrieval layer. Use it for concise
  cross-session state, decisions, pointers, handoffs, and routine observations.
- **Obsidian** is the human-readable layer. Use it for project documents,
  meeting records, daily timelines, decisions, and audit history.
- **The local profile** identifies the agent, environment, Vault, and service
  endpoint. It never contains the AgentMemory secret.

The service URL and Vault path are installation-specific. Read
[`references/configuration.md`](references/configuration.md) before onboarding.

## Write Contract

| Tier | Use for | Destination |
|---|---|---|
| Memory | Durable state, decisions, pointers, handoffs | AgentMemory + concise Obsidian current-state record |
| Project | Plans, debugging history, design rationale, long reports | Project directory in Obsidian |
| Routine | What happened during a work session | Obsidian dated log + AgentMemory observation |

Memory is an index, not a transcript store. Keep AgentMemory entries concise,
factual, and searchable. Put full explanations in the project directory and
link to them from memory when future agents need the pointer.

Use the helper scripts for tier 1 and tier 3 writes when possible:

```bash
python3 scripts/write_log.py \
  --actor "$CO_MEMORY_ACTOR_ID" \
  --project "project-slug" \
  --action "Describe the completed action" \
  --status success

python3 scripts/write_handoff.py \
  --from "$CO_MEMORY_ACTOR_ID" \
  --to "next-agent" \
  --project "project-slug" \
  --summary "Current state" \
  --next "Next action"
```

If AgentMemory delivery fails, the helper writes a retryable outbox and exits
non-zero by default. Restore connectivity and run
`python3 scripts/doctor.py --flush-outbox`. Use `--allow-pending` only when a
temporary one-layer state is explicitly acceptable.

## Identity And Projects

- `actor_id` identifies the runtime or Bot that wrote the record. A single
  runtime can use `codex`; a multi-Bot runtime can use `platform.bot`.
- `project_id` identifies the work being done. Use a stable lowercase slug such
  as `research-notes` or `shared-memory`.
- `runtime_id`, `environment_id`, `actor_id`, `project_id`, and `session_id`
  are separate fields. Do not use chat titles or display names as IDs.
- Display names may change; stable IDs should not.

## Session Start

Read the shared index and writing protocol in `Agent_Comemory/00_Index/` and
`Agent_Comemory/01_Shared/` when present. Then retrieve only the memory slots
and project context relevant to the current task:

`user_preferences`, `tool_guidelines`, `project_context`, `guidance`,
`pending_items`, and the active project's context.

Use targeted retrieval before opening many Obsidian files. AgentMemory is the
index and retrieval layer; Obsidian is the source material. Read another
agent's records when continuing a task, handling a rollback, changing shared
infrastructure, or when the conversation clearly refers to earlier work.

## Obsidian Rules

The recommended workspace is:

```text
Agent_Comemory/
├── 00_Index/
├── 01_Shared/
├── 02_Agents/<actor-id>.md
├── 02_Projects/<project-id>/
├── 03_Logs/YYYY/YYYY-MM/YYYY-MM-DD.md
├── 04_Decisions/
├── 05_Handoffs/YYYY/YYYY-MM/
└── 09_Archive/<project-id>/
```

The recommended personal wiki is `Personal_Wiki/`:

```text
Personal_Wiki/
├── 01_Daily/YYYY/YYYY-MM-DD.md
├── 02_Inbox/
├── 03_People/
├── 04_Meetings/
├── 05_Projects/
├── 06_Investments/
├── 07_Links/
├── 08_Knowledge/
└── 09_Archive/
```

Daily notes use one file per date under a year folder. A dated real-world event
that creates or updates a meeting, person, project, or investment note gets one
concise linked timeline entry. If the date is uncertain, use Inbox instead of
guessing. Agent operations belong in `Agent_Comemory/03_Logs/`.

Completed projects move to the corresponding `09_Archive/` path after an
explicit archive decision. Preserve historical mentions and logs. Update
current indexes, pending items, and navigation links so they point to the
archive. Reopen only with an explicit decision record.

## Security

Never write API keys, passwords, tokens, cookies, private keys, or complete
credentials to AgentMemory, Obsidian, logs, handoffs, profiles, or commits.
Use runtime environment injection for `AGENTMEMORY_SECRET`.

## References

- [Configuration](references/configuration.md)
- [MCP onboarding](references/mcp-onboarding.md)
- [Obsidian collaboration](references/obsidian-collaboration.md)
- [AgentMemory integration](references/agentmemory-integration.md)
