#!/usr/bin/env python3
"""Write a co-memory log to Obsidian and AgentMemory with a retryable outbox."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import zoneinfo
from pathlib import Path
from typing import Optional

from dual_write import actor_id, agent_comemory_root, agentmemory_url, deliver_or_queue, timezone_name


def write_obsidian(
    actor: str, project: str, action: str, status: str, files: str, note: str,
    ts: str, date_str: str, year: int, month: int,
) -> Path:
    log_dir = agent_comemory_root() / "03_Logs" / str(year) / f"{year}-{month:02d}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{date_str}.md"

    lines = [
        f"## {ts} | {actor} | {project}",
        "",
        f"- 动作：{action}",
        f"- 状态：{status}",
    ]
    if files:
        lines.append("- 文件：" + "，".join(f"`{item.strip()}`" for item in files.split(",") if item.strip()))
    if note:
        lines.append(f"- 备注：{note}")
    lines.append("")

    mode = "a" if log_path.exists() else "w"
    with log_path.open(mode, encoding="utf-8") as handle:
        if mode == "w":
            handle.write(f"# {date_str}\n\n")
        handle.write("\n".join(lines) + "\n")
    return log_path


def build_payload(actor: str, project: str, action: str, status: str, files: str, note: str, ts: str) -> dict:
    parts = [f"[{ts}] [{actor}] [{project}] {action}", f"status: {status}"]
    if files:
        parts.append(f"files: {files}")
    if note:
        parts.append(f"note: {note}")
    return {
        "content": "\n".join(parts),
        "project": project,
        "agentId": actor,
        "concepts": ["co-memory-log", project, actor, f"status:{status}", *( ["has-files"] if files else [])],
        "metadata": {
            "source": "co-memory-system/write_log.py",
            "actor_id": actor,
            "project": project,
            "status": status,
            "action": action,
            "files": files,
            "note": note,
            "timestamp": ts,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reliable co-memory log writer")
    parser.add_argument("--actor", default=actor_id(), help="Override configured actor_id")
    parser.add_argument("--project", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--status", default="info")
    parser.add_argument("--files", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--skip-agentmemory", action="store_true", help="Intentional Obsidian-only write")
    parser.add_argument("--allow-pending", action="store_true", help="Exit 0 after queueing a failed AgentMemory write")
    args = parser.parse_args(argv)

    if not args.actor:
        parser.error("Provide --actor, CO_MEMORY_ACTOR_ID, or actor_id in the local profile")
    if not args.skip_agentmemory:
        try:
            agentmemory_url()
        except ValueError as exc:
            parser.error(str(exc))
    root = agent_comemory_root()
    if not (root / "00_Index" / "README.md").is_file():
        parser.error("Configured Vault is not initialized: Agent_Comemory/00_Index/README.md missing")

    now = datetime.datetime.now(zoneinfo.ZoneInfo(timezone_name()))
    ts = now.strftime("%Y-%m-%d %H:%M %Z")
    log_path = write_obsidian(
        args.actor, args.project, args.action, args.status, args.files, args.note,
        ts, now.strftime("%Y-%m-%d"), now.year, now.month,
    )
    print(f"[OK] Obsidian log     -> {log_path}")

    if args.skip_agentmemory:
        print("[SKIP] AgentMemory    -> intentional Obsidian-only write")
        return 0

    result = deliver_or_queue(
        build_payload(args.actor, args.project, args.action, args.status, args.files, args.note, ts),
        "log",
    )
    if result.status == "delivered":
        print(f"[OK] AgentMemory      -> POST {agentmemory_url()}/agentmemory/remember")
        return 0

    print(f"[PENDING] AgentMemory -> {result.detail}; event={result.event_id}; outbox={result.outbox}")
    return 0 if args.allow_pending else 2


if __name__ == "__main__":
    sys.exit(main())
