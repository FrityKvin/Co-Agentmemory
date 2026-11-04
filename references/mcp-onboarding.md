# MCP Onboarding

Each agent client owns its MCP configuration. This repository provides the
shared Skill and optional helpers; `agents/openai.yaml` is UI metadata, not a
universal MCP configuration.

## Stdio Pattern

AgentMemory provides an MCP shim. Follow the upstream package documentation for
the version compatible with your deployment. A client-specific configuration
usually contains a command, arguments, and environment variables:

```json
{
  "command": "npx",
  "args": ["-y", "@agentmemory/mcp"],
  "env": {
    "AGENTMEMORY_URL": "https://memory.example.com",
    "AGENTMEMORY_SECRET": "<injected-by-client-secret-store>"
  }
}
```

This is a shape example, not a directly importable configuration for every
client. Prefer a client secret store or environment injection over placing a
literal secret in configuration. Consult the target client's documentation for
its exact file format and restart behavior.

## Validation

1. Confirm the service health endpoint is reachable.
2. Confirm the target client can list or invoke AgentMemory tools.
3. Perform an authenticated read against the intended service.
4. When write verification is needed, use a clearly marked test record and
   remove it using the service's supported deletion mechanism.
5. Confirm the agent can access the configured Obsidian Vault.

An MCP tool listing alone does not prove that automatic memory capture or
lifecycle hooks are enabled. A health endpoint alone does not prove that
authentication, search, or writes work.

