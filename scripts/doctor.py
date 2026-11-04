#!/usr/bin/env python3
"""
Co-Memory doctor: health check for shared memory system (scaffolding mode).

This is ADVISORY ONLY. It reports warnings and suggestions,
but NEVER blocks any operation. You are always free to:
  - edit Obsidian files directly
  - call any AgentMemory MCP tool directly
  - ignore any suggestion from this script

Checks:
  - Obsidian vault exists
  - index / shared rules exist
  - project folder exists
  - today log exists
  - AgentMemory MCP reachable via stdio
  - core slots readable
"""

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import zoneinfo
from typing import Dict, List, Optional

from dual_write import (
    agent_comemory_root,
    agentmemory_secret,
    agentmemory_url,
    flush_outbox,
    outbox_path,
    pending_count,
    vault_root,
    personal_wiki_root,
    timezone_name,
    actor_id,
    local_profile,
    setting,
)

DEFAULT_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MCP_CMD = shlex.split(os.environ.get("CO_MEMORY_MCP_COMMAND", "npx -y @agentmemory/mcp"))
SKILL_DIR = os.environ.get("CO_MEMORY_SKILL_DIR", DEFAULT_SKILL_DIR)
CORE_SLOTS = [
    "user_preferences",
    "tool_guidelines",
    "persona",
    "project_context",
    "guidance",
    "pending_items",
]
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*\.[a-z0-9][a-z0-9._-]*$")


def run_mcp_tool(method: str, params: Dict) -> Optional[Dict]:
    """Call an MCP tool through a complete initialize -> call stdio exchange."""
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "co-memory-doctor", "version": "0.5.0"},
        },
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": method, "arguments": params},
    }
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    try:
        result = subprocess.run(
            MCP_CMD,
            input="\n".join(json.dumps(message) for message in (initialize, initialized, payload)) + "\n",
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **os.environ,
                "AGENTMEMORY_URL": AGENTMEMORY_URL,
                **({"AGENTMEMORY_SECRET": AGENTMEMORY_SECRET} if AGENTMEMORY_SECRET else {}),
            },
        )
    except Exception as e:
        print(f"[WARN] MCP call failed: {e}")
        return None

    if result.returncode != 0:
        print(f"[WARN] MCP exit {result.returncode}: {result.stderr}")
        return None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("id") != 2 or "result" not in data:
            continue
        tool_result = data["result"]
        if isinstance(tool_result, dict) and "slots" in tool_result:
            return tool_result
        for item in tool_result.get("content", []) if isinstance(tool_result, dict) else []:
            if item.get("type") != "text":
                continue
            try:
                parsed = json.loads(item.get("text", ""))
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    return None


def check_http_health(url: str) -> bool:
    """Use AgentMemory's documented health endpoint instead of treating a root 404 as healthy."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(f"{url.rstrip('/')}/agentmemory/livez", method="GET")
    if AGENTMEMORY_SECRET:
        request.add_header("Authorization", f"Bearer {AGENTMEMORY_SECRET}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.getcode() < 300
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def get_git_commit(path: str) -> Optional[str]:
    """Get short git commit hash for a repo."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_context_skill_commit(path: str) -> Optional[str]:
    """Read the source revision explicitly recorded in the shared system context."""
    try:
        with open(path, encoding="utf-8") as context_file:
            for line in context_file:
                match = re.match(r"^- `skill_source_commit`: `([0-9a-f]{7,40})`$", line.strip())
                if match:
                    return match.group(1)
    except OSError:
        return None
    return None


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--onboard" in argv:
        from onboard import main as onboard_main
        return onboard_main([arg for arg in argv if arg != "--onboard"])
    parser = argparse.ArgumentParser(description="Co-Memory health and outbox recovery check")
    parser.add_argument("--onboard", action="store_true", help="Confirm identity and create a local profile")
    parser.add_argument(
        "--check-mcp",
        action="store_true",
        help="Also validate the local stdio MCP bridge and core slots.",
    )
    parser.add_argument(
        "--flush-outbox",
        action="store_true",
        help="Retry AgentMemory observations queued after prior dual-write failures.",
    )
    args = parser.parse_args(argv)
    global VAULT_ROOT, AGENT_COMEMORY, PERSONAL_WIKI, AGENTMEMORY_URL, AGENTMEMORY_SECRET
    try:
        VAULT_ROOT = str(vault_root())
        AGENT_COMEMORY = str(agent_comemory_root())
        PERSONAL_WIKI = str(personal_wiki_root())
        AGENTMEMORY_URL = agentmemory_url()
        AGENTMEMORY_SECRET = agentmemory_secret()
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    tz = zoneinfo.ZoneInfo(timezone_name())
    now = datetime.datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")

    print("Co-Memory Doctor (scaffolding mode — advisory only)")
    print("=" * 50)

    print(f"Actor:              {actor_id() or 'UNCONFIGURED'}")
    print(f"Environment:        {setting('CO_MEMORY_ENVIRONMENT_ID', 'environment_id') or 'UNCONFIGURED'}")
    print(f"Local profile:      {'configured' if local_profile() else 'absent (environment/defaults)'}")
    print("Registration:       not checked; local configuration does not prove central registration")

    warnings = []

    if not actor_id():
        warnings.append("Actor identity not configured")
    if not setting("CO_MEMORY_ENVIRONMENT_ID", "environment_id"):
        warnings.append("Environment identity not configured")

    # 1. Check Obsidian vault
    vault_ok = os.path.isdir(VAULT_ROOT)
    agent_comemory_ok = os.path.isdir(AGENT_COMEMORY)
    personal_wiki_ok = os.path.isdir(PERSONAL_WIKI)
    print(f"Obsidian vault:      {'OK' if vault_ok else 'MISSING'}")
    print(f"Agent_Comemory:      {'OK' if agent_comemory_ok else 'MISSING'}")
    print(f"Personal_Wiki:       {'OK' if personal_wiki_ok else 'MISSING'}")
    if not vault_ok:
        warnings.append(f"Vault not found at {VAULT_ROOT}")
    if not agent_comemory_ok:
        warnings.append(f"Agent_Comemory not found at {AGENT_COMEMORY}")
    if not personal_wiki_ok:
        warnings.append(f"Personal wiki not found at {PERSONAL_WIKI}")

    # 2. Check index and shared rules
    index_ok = os.path.exists(os.path.join(VAULT_ROOT, "00_Index", "README.md"))
    agent_index_ok = os.path.exists(os.path.join(AGENT_COMEMORY, "00_Index", "README.md"))
    project_id_rule_ok = os.path.exists(
        os.path.join(AGENT_COMEMORY, "01_Shared", "Project ID Rule.md")
    )
    writing_protocol_ok = os.path.exists(
        os.path.join(AGENT_COMEMORY, "01_Shared", "Agent Writing Protocol.md")
    )
    print(f"Index exists:        {'OK' if index_ok else 'MISSING'}")
    print(f"Agent index exists:  {'OK' if agent_index_ok else 'MISSING'}")
    print(f"Project ID rule:     {'OK' if project_id_rule_ok else 'MISSING'}")
    print(f"Writing protocol:    {'OK' if writing_protocol_ok else 'MISSING'}")
    if not index_ok:
        warnings.append("00_Index/README.md not found")
    if not agent_index_ok:
        warnings.append("Agent_Comemory/00_Index/README.md not found")
    if not project_id_rule_ok:
        warnings.append("01_Shared/Project ID Rule.md not found")
    if not writing_protocol_ok:
        warnings.append("01_Shared/Agent Writing Protocol.md not found")

    # 3. Check today log
    log_path = os.path.join(
        AGENT_COMEMORY, "03_Logs", str(now.year), f"{now.year}-{now.month:02d}", f"{date_str}.md"
    )
    log_ok = os.path.exists(log_path)
    print(f"Today log exists:    {'OK' if log_ok else 'MISSING'}")
    if not log_ok:
        warnings.append(f"Today's log not yet created: {log_path}")

    # 4. Check AgentMemory's documented health endpoint and pending dual-write events.
    http_ok = check_http_health(AGENTMEMORY_URL)
    print(f"\nAgentMemory HTTP:    {'OK' if http_ok else 'UNREACHABLE'} ({AGENTMEMORY_URL}/agentmemory/livez)")

    if not http_ok:
        warnings.append(f"AgentMemory HTTP endpoint unreachable at {AGENTMEMORY_URL}")

    queued = pending_count()
    print(f"AgentMemory outbox:  {queued} pending")
    if args.flush_outbox and queued:
        flushed = flush_outbox()
        print(
            "Outbox flush:        "
            f"delivered={flushed['delivered']} pending={flushed['pending']} invalid={flushed['invalid']}"
        )
        queued = pending_count()
    if queued:
        warnings.append(f"{queued} AgentMemory write(s) pending in {outbox_path()}")

    if args.check_mcp:
        print("AgentMemory MCP:     checking...")
        mcp_ok = False
        slots_ok = {}
        try:
            result = run_mcp_tool("memory_slot_list", {})
            if result and isinstance(result, dict):
                mcp_ok = True
                slot_labels = {s.get("label") for s in result.get("slots", [])}
                for slot in CORE_SLOTS:
                    slots_ok[slot] = slot in slot_labels
        except Exception as e:
            print(f"  [WARN] Exception: {e}")

        print(f"AgentMemory MCP:     {'OK' if mcp_ok else 'UNREACHABLE'}")
        if mcp_ok:
            missing = [slot for slot, present in slots_ok.items() if not present]
            if missing:
                warnings.append(f"Missing core slots: {', '.join(missing)}")
            else:
                print("  All core slots present")
        else:
            warnings.append("AgentMemory MCP bridge unavailable; HTTP dual-write can still work")
    else:
        print("AgentMemory MCP:     skipped (pass --check-mcp to validate local bridge)")

    # 7. Optionally compare a recorded skill revision when the host provides one.
    skill_commit = get_git_commit(SKILL_DIR)
    if skill_commit:
        print(f"\nSkill repo commit:    {skill_commit}")
        context_path = setting("CO_MEMORY_CONTEXT_PATH", "context_path")
        if context_path:
            context_commit = get_context_skill_commit(context_path)
            print(f"Context revision:     {context_commit or 'MISSING'}")
            if context_commit and context_commit != skill_commit:
                warnings.append(
                    f"Context records skill revision {context_commit}, but source is {skill_commit}."
                )

    print("=" * 60)

    if warnings:
        print("\n[INFO] Warnings found (advisory only — you may ignore):")
        for w in warnings:
            print(f"  • {w}")
    else:
        print("\n[OK] No issues found.")

    print("\n[INFO] This script does not block any operation.")
    print("[INFO] You are always free to call MCP or edit files directly.")

    # Always return 0 — doctor never "fails"
    return 0


if __name__ == "__main__":
    sys.exit(main())
