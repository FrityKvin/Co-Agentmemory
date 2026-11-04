# Co-Agentmemory

An open, vendor-neutral skill for sharing durable context between AI agents
through AgentMemory and an Obsidian vault.

[简体中文](./README.zh-CN.md)

The project defines a small operating protocol and optional Python helpers:

- AgentMemory stores concise, searchable machine memory.
- Obsidian stores human-readable records, project detail, and audit history.
- Agents keep one stable identity and project slug across runtimes.
- Tier 1 state and routine logs are written to both layers.
- Long project detail stays in the project's Obsidian directory.

This repository contains no hosted service, API key, default endpoint, personal
path, or vendor-specific agent configuration. You supply those values locally.

## Start Here

1. Read [`SKILL.md`](./SKILL.md) or [`SKILL.zh-CN.md`](./SKILL.zh-CN.md).
2. Read [`references/configuration.md`](./references/configuration.md).
3. Connect the AgentMemory MCP server using your client's native configuration.
4. Run the onboarding helper after preparing an Obsidian vault:

Create `Agent_Comemory/00_Index/README.md` inside the existing Vault first.

```bash
python3 scripts/onboard.py \
  --runtime codex \
  --environment laptop \
  --vault /absolute/path/to/vault \
  --agentmemory-url https://memory.example.com
```

The profile contains paths and identity only. Set `AGENTMEMORY_SECRET` in the
runtime environment; never put it in a profile or repository.

To install the Skill, place this repository's contents in a directory named
`co-agentmemory` in your agent's supported Skill location and reload the
client. Installation and MCP configuration are separate steps; supported
locations depend on the client.

## Recommended Vault Layout

```text
Vault/
├── Personal_Wiki/
│   ├── 01_Daily/YYYY/YYYY-MM-DD.md
│   ├── 02_Inbox/
│   ├── 03_People/
│   ├── 04_Meetings/
│   ├── 05_Projects/
│   ├── 06_Investments/
│   ├── 07_Links/
│   ├── 08_Knowledge/
│   └── 09_Archive/
└── Agent_Comemory/
    ├── 00_Index/
    ├── 01_Shared/
    ├── 02_Agents/
    ├── 02_Projects/
    ├── 03_Logs/YYYY/YYYY-MM/YYYY-MM-DD.md
    ├── 04_Decisions/
    ├── 05_Handoffs/YYYY/YYYY-MM/*.md
    └── 09_Archive/
```

`Personal_Wiki` is a recommended name, not a required one. Set
`personal_wiki_dir` in the profile or `CO_MEMORY_PERSONAL_WIKI_DIR` when your
vault uses another name.

## Scripts

- `scripts/onboard.py` creates a local identity profile without credentials.
- `scripts/write_log.py` writes a routine log to Obsidian and AgentMemory.
- `scripts/write_handoff.py` writes a handoff to both layers.
- `scripts/doctor.py` checks the vault, AgentMemory health, MCP bridge, and
  pending outbox events.

When AgentMemory is unavailable, the helpers keep a JSONL outbox and return a
non-zero status unless `--allow-pending` is explicitly provided. Retry with:

```bash
python3 scripts/doctor.py --flush-outbox
```

## Client Configuration

`agents/openai.yaml` contains only OpenAI/Codex-style UI metadata. It does not
configure MCP for other clients. See
[`references/mcp-onboarding.md`](./references/mcp-onboarding.md) for the
client-neutral stdio pattern and the boundary between this repository and a
client's own configuration.

## Development

The helpers require Python 3.10 or newer and use only the standard library
(on Windows, install the `tzdata` package if IANA timezone data is unavailable):

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

## License

MIT. See [`LICENSE`](./LICENSE).
