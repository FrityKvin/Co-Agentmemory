# Obsidian Collaboration

## Roles

The human owns the Vault. Agents can write first-hand records directly; a
curator may organize them later, but should not become the only write path.
Separate personal records from agent operational records. The recommended
directories are `Personal_Wiki/` and `Agent_Comemory/`, configurable per Vault.

## Agent Workspace

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

The originating agent writes the first-hand log and, when another session
needs explicit continuation, a handoff. A curator may synthesize current state
without erasing the original observation. Long project detail remains in the
project directory; AgentMemory stores state and pointers.

## Personal Daily

Recommended path: `Personal_Wiki/01_Daily/YYYY/YYYY-MM-DD.md`.
Use one file per calendar date. Before creating one, check the canonical path
and search for the date to avoid duplicates. Daily is a concise timeline and
date index, not a copy of meeting minutes or investment ledgers.

For an already-occurred real-world event with a reliable date, link the Daily
entry to its meeting, person, project, or investment note. Use the event date,
not the processing date. If an event is recorded later, record the capture date
and source when useful. Put uncertain dates in Inbox instead of guessing.
Keep personal prose and historical entries intact; do not batch-rewrite them to
fit a template. Agent deployments, tool calls, and code changes belong in the
agent log rather than the personal Daily.

Suggested minimal template:

```md
---
date: YYYY-MM-DD
type: daily
---

# YYYY-MM-DD

## Timeline

## Follow-up
```

The follow-up section is optional. Use the Vault owner's language and existing
template when one already exists.

## Archive

When the owner explicitly completes, stops, or archives a project, move its
active project folder to the corresponding `09_Archive/<project-id>/` path.
Record the date, reason, and destination in the relevant index. Keep memory
history for retrieval and mark current state archived or stopped.

Preserve historical Daily entries, meeting notes, decisions, logs, handoffs,
and references. Update current indexes, active tasks, guidance, pending items,
runbooks, and essential links so they point to the archive or say the project
is no longer active. Reopening requires an explicit decision.

