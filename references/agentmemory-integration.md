# AgentMemory Integration

Use the [upstream AgentMemory documentation](https://github.com/rohitg00/agentmemory)
for installation, supported MCP tools, API versions, deployment, and release
notes. This file documents the generic contract used by this Skill; it does not
replace the upstream manual.

## Retrieval

1. Read relevant stable slots and project context.
2. Use a targeted recall or search with a stable project ID.
3. Open the Obsidian documents named by the result, index, or handoff.
4. Expand the search only when necessary; report uncertainty rather than
   inventing missing history.

This keeps AgentMemory as a compact retrieval layer and Obsidian as readable
source material. Availability of an MCP tool does not enable automatic capture.

## Writes

The bundled helpers send `content`, `project`, `agentId`, and `concepts` to
`/agentmemory/remember`, then validate the response. They also write an
Obsidian artifact. Failed delivery is retained in a local JSONL outbox and can
be retried with `doctor.py --flush-outbox`.

These helpers target the AgentMemory 0.9.31 response shape. Confirm API
compatibility with your server version before production use. Project filters
are retrieval aids, not access-control boundaries. A timeout may have saved a
record; retries are at-least-once and can create duplicates.

## Operating Boundaries

- Supply the URL and credential from the agent's own configuration.
- Do not scan another agent's configuration to recover secrets.
- Keep test records clearly marked and delete them after verification.
- Validate health, authentication, search, and write delivery separately.
- Protect backups and outbox files as private data; they can contain memory text.
