#!/usr/bin/env python3
"""Confirm a runtime identity and create one local co-memory profile."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import urllib.error
import urllib.request
import zoneinfo
from pathlib import Path

from dual_write import DEFAULT_AGENT_COMEMORY_DIR, DEFAULT_PERSONAL_WIKI_DIR, DEFAULT_TIMEZONE


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def confirmed(value: str | None, label: str, suggestion: str = "", optional: bool = False) -> str:
    if value is not None:
        return value.strip()
    if not sys.stdin.isatty():
        if suggestion or optional:
            return suggestion
        raise ValueError(f"{label} required in non-interactive mode")
    hint = f" [{suggestion}]" if suggestion else ""
    response = input(f"{label}{hint}: ").strip()
    return response or suggestion


def check_agentmemory(url: str, secret: str) -> str:
    request = urllib.request.Request(f"{url}/agentmemory/livez", method="GET")
    if secret:
        request.add_header("Authorization", f"Bearer {secret}")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return "reachable" if response.status == 200 else f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError):
        return "unreachable"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a local co-memory actor profile")
    parser.add_argument("--runtime", help="Stable platform ID, e.g. codex or hermes")
    parser.add_argument("--bot", help="Stable Bot ID; omit for a single-identity runtime")
    parser.add_argument("--display-name", help="Human-readable name")
    parser.add_argument("--environment", help="Stable device or bridge ID")
    parser.add_argument("--vault", help="Absolute path to an existing Obsidian Vault")
    parser.add_argument("--agent-comemory-dir", default=DEFAULT_AGENT_COMEMORY_DIR, help="Agent workspace path relative to the Vault")
    parser.add_argument("--personal-wiki-dir", default=DEFAULT_PERSONAL_WIKI_DIR, help="Personal wiki path relative to the Vault")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="IANA timezone used for generated logs")
    parser.add_argument("--agentmemory-url", help="AgentMemory REST URL")
    parser.add_argument("--profile", help="Profile output path; defaults to a per-actor file")
    parser.add_argument("--reconfigure", action="store_true", help="Replace an existing profile")
    args = parser.parse_args(argv)

    try:
        runtime = confirmed(args.runtime, "Runtime ID").lower()
        bot = confirmed(args.bot, "Bot ID (blank for a single-identity runtime)", optional=True).lower() if args.bot is not None or sys.stdin.isatty() else ""
        if not ID_PATTERN.fullmatch(runtime) or (bot and not ID_PATTERN.fullmatch(bot)):
            raise ValueError("Runtime and Bot IDs must use lowercase letters, digits, _ or -")
        actor = f"{runtime}.{bot}" if bot else runtime
        display_name = confirmed(args.display_name, "Display name", actor)
        environment = confirmed(args.environment, "Environment ID", platform.node().lower()).lower()
        if not ID_PATTERN.fullmatch(environment):
            raise ValueError("Environment ID must use lowercase letters, digits, _ or -")
        suggested_vault = ""
        vault_value = confirmed(args.vault, "Local Obsidian Vault path", suggested_vault)
        vault = Path(vault_value).expanduser()
        for directory in (args.agent_comemory_dir, args.personal_wiki_dir):
            if not directory or Path(directory).is_absolute() or ".." in Path(directory).parts:
                raise ValueError("Workspace directories must be safe paths relative to the Vault")
        try:
            zoneinfo.ZoneInfo(args.timezone)
        except zoneinfo.ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {args.timezone}") from exc
        if not vault.is_absolute() or not (vault / args.agent_comemory_dir / "00_Index/README.md").is_file():
            raise ValueError("Vault must be an existing absolute path with the Agent_Comemory index")
        url = confirmed(args.agentmemory_url, "AgentMemory URL")
        if not url.startswith(("http://", "https://")):
            raise ValueError("AgentMemory URL must start with http:// or https://")
        path = Path(args.profile or os.environ.get("CO_MEMORY_PROFILE") or f"~/.config/co-agentmemory/profiles/{actor}.json").expanduser()
        if not path.is_absolute():
            raise ValueError("Profile path must be absolute")
        if path.exists() and not args.reconfigure:
            raise ValueError(f"Profile already exists: {path}; use --reconfigure to replace it")

        profile = {
            "schema_version": 1,
            "runtime_id": runtime,
            "actor_id": actor,
            "display_name": display_name,
            "environment_id": environment,
            "vault_root": str(vault.resolve()),
            "agent_comemory_dir": args.agent_comemory_dir,
            "personal_wiki_dir": args.personal_wiki_dir,
            "timezone": args.timezone,
            "agentmemory_url": url,
        }
        print(json.dumps(profile, ensure_ascii=False, indent=2))
        if sys.stdin.isatty() and input("Create this profile? [y/N]: ").strip().lower() != "y":
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(profile, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        print(f"Local profile: {path}")
        print(f"Vault: ready | AgentMemory: {check_agentmemory(url, os.environ.get('AGENTMEMORY_SECRET', ''))}")
        print("Authentication: not verified | Central registration: not checked")
        print(f"Select with CO_MEMORY_PROFILE={path}")
        return 0
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
