#!/usr/bin/env python3
"""Write a co-memory handoff to Obsidian and AgentMemory with a retryable outbox."""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import zoneinfo
from pathlib import Path
from typing import Optional

from dual_write import agent_comemory_root, agentmemory_url, deliver_or_queue, timezone_name


def write_obsidian(
    sender: str, receiver: str, project: str, summary: str, next_action: str,
    blocker: str, files: str, ts: str, slug: str,
) -> Path:
    handoff_dir = agent_comemory_root() / "05_Handoffs" / ts[:4] / ts[:7]
    handoff_dir.mkdir(parents=True, exist_ok=True)
    path = handoff_dir / f"{slug}-{sender}-to-{receiver}.md"

    lines = [
        f"# Handoff: {sender} -> {receiver}",
        "",
        f"- 项目：`{project}`",
        f"- 时间：{ts}",
        f"- 摘要：{summary}",
        f"- 下一步：{next_action}",
        f"- 已知阻塞：{blocker}",
    ]
    if files:
        lines.append("- 相关文件：")
        lines.extend(f"  - `{item.strip()}`" for item in files.split(",") if item.strip())
    lines.extend(["", "---", ""])
    with path.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def build_payload(
    sender: str, receiver: str, project: str, summary: str, next_action: str,
    blocker: str, files: str, ts: str,
) -> dict:
    content = "\n".join([
        f"[HANDOFF {ts}] {sender} -> {receiver} ({project})",
        f"summary: {summary}",
        f"next: {next_action}",
        f"blocker: {blocker}",
        *( [f"files: {files}"] if files else []),
    ])
    concepts = ["handoff", project, f"from:{sender}", f"to:{receiver}"]
    if blocker and blocker.lower() != "none":
        concepts.append("has-blocker")
    return {
        "content": content,
        "project": project,
        "agentId": sender,
        "concepts": concepts,
        "metadata": {
            "source": "co-memory-system/write_handoff.py",
            "type": "handoff",
            "from": sender,
            "to": receiver,
            "project": project,
            "summary": summary,
            "next": next_action,
            "blocker": blocker,
            "files": files,
            "timestamp": ts,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reliable co-memory handoff writer")
    parser.add_argument("--from", dest="sender", required=True)
    parser.add_argument("--to", dest="receiver", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--next", default="")
    parser.add_argument("--blocker", default="None")
    parser.add_argument("--files", default="")
    parser.add_argument("--skip-agentmemory", action="store_true", help="Intentional Obsidian-only write")
    parser.add_argument("--allow-pending", action="store_true", help="Exit 0 after queueing a failed AgentMemory write")
    args = parser.parse_args(argv)

    if not all(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", item) for item in (args.sender, args.receiver)):
        parser.error("Agent IDs must contain only letters, digits, dots, underscores or hyphens")
    if not args.skip_agentmemory:
        try:
            agentmemory_url()
        except ValueError as exc:
            parser.error(str(exc))
    if not (agent_comemory_root() / "00_Index" / "README.md").is_file():
        parser.error("Configured Vault is not initialized: agent workspace index missing")

    now = datetime.datetime.now(zoneinfo.ZoneInfo(timezone_name()))
    ts = now.strftime("%Y-%m-%d %H:%M %Z")
    path = write_obsidian(
        args.sender, args.receiver, args.project, args.summary, args.next,
        args.blocker, args.files, ts, now.strftime("%Y%m%d-%H%M"),
    )
    print(f"[OK] Obsidian handoff -> {path}")

    if args.skip_agentmemory:
        print("[SKIP] AgentMemory    -> intentional Obsidian-only write")
        return 0

    result = deliver_or_queue(
        build_payload(
            args.sender, args.receiver, args.project, args.summary, args.next,
            args.blocker, args.files, ts,
        ),
        "handoff",
    )
    if result.status == "delivered":
        print(f"[OK] AgentMemory      -> POST {agentmemory_url()}/agentmemory/remember")
        return 0

    print(f"[PENDING] AgentMemory -> {result.detail}; event={result.event_id}; outbox={result.outbox}")
    return 0 if args.allow_pending else 2


if __name__ == "__main__":
    sys.exit(main())
