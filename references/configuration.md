# Configuration

The helpers resolve configuration from environment variables, then an optional
local JSON profile. Credentials are accepted only from the process environment.
No endpoint or Vault path is built into this repository.

## Local Profile

Default profile location: `~/.config/co-agentmemory/profile.json`.
Set `CO_MEMORY_PROFILE` to use a different profile, for example one per Bot.

```json
{
  "schema_version": 1,
  "runtime_id": "example-runtime",
  "actor_id": "example-runtime.assistant",
  "display_name": "Assistant",
  "environment_id": "laptop",
  "vault_root": "/absolute/path/to/vault",
  "agent_comemory_dir": "Agent_Comemory",
  "personal_wiki_dir": "Personal_Wiki",
  "timezone": "UTC",
  "agentmemory_url": "https://memory.example.com"
}
```

The profile contains no secrets. Keep the file outside the public repository.
Each device supplies its own `vault_root` and endpoint. A remote agent without
a Vault-capable filesystem or bridge cannot complete the Obsidian half.

| Profile field | Environment override |
|---|---|
| `actor_id` | `CO_MEMORY_ACTOR_ID` |
| `environment_id` | `CO_MEMORY_ENVIRONMENT_ID` |
| `vault_root` | `CO_MEMORY_VAULT_ROOT` |
| `agent_comemory_dir` | `CO_MEMORY_AGENT_COMEMORY_DIR` |
| `personal_wiki_dir` | `CO_MEMORY_PERSONAL_WIKI_DIR` |
| `timezone` | `CO_MEMORY_TIMEZONE` |
| `agentmemory_url` | `AGENTMEMORY_URL` |
| optional `context_path` | `CO_MEMORY_CONTEXT_PATH` |

`AGENTMEMORY_SECRET` is environment-only. Inject it into the executing agent's
runtime using that platform's secret mechanism; never put the secret in the
profile, Skill, command history, logs, or shared memory.

## First-Time Setup

Create the agent workspace index first:

```text
<vault>/Agent_Comemory/00_Index/README.md
```

Then run:

```bash
python3 scripts/onboard.py \
  --runtime example-runtime \
  --environment laptop \
  --vault /absolute/path/to/vault \
  --agentmemory-url https://memory.example.com \
  --timezone UTC
```

The helper creates a per-actor profile under `~/.config/co-agentmemory/profiles/`.
Select it with `CO_MEMORY_PROFILE` using the path printed by the helper.
An interactive run confirms the profile before creating it. Existing profiles
are not replaced without `--reconfigure`. A Bot uses `--bot <stable-id>`.
The helper checks the Vault and endpoint, but does not register an actor in a
central registry or prove authenticated read/write access.

## Health And Recovery

```bash
python3 scripts/doctor.py
python3 scripts/doctor.py --check-mcp
python3 scripts/doctor.py --flush-outbox
```

Health/liveness is not proof of authentication or successful retrieval. Validate
the exact client route separately. An outbox retry is at-least-once: a request
that timed out may already have been accepted by the server, so duplicate
records are possible. Check the resulting memory when correctness matters.

## Supported Layout

The default `agent_comemory_dir` is `Agent_Comemory`. The default personal wiki
name is `Personal_Wiki`. Both can be changed to safe paths relative to the
configured Vault; the writers use the configured agent workspace. The personal
wiki layout is a recommendation, not a schema enforced by the scripts.

