#!/usr/bin/env python3
"""Small shared helpers for reliable AgentMemory + Obsidian dual writes."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt


DEFAULT_AGENT_COMEMORY_DIR = "Agent_Comemory"
DEFAULT_PERSONAL_WIKI_DIR = "Personal_Wiki"
DEFAULT_TIMEZONE = "UTC"


def local_profile() -> dict[str, Any]:
    path = Path(os.environ.get("CO_MEMORY_PROFILE", "~/.config/co-agentmemory/profile.json")).expanduser()
    if not path.exists():
        if "CO_MEMORY_PROFILE" in os.environ:
            raise ValueError(f"Configured profile does not exist: {path}")
        return {}
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("Co-memory profile must be an object with schema_version=1")
    return profile


def setting(env: str, key: str, default: str = "") -> str:
    value = os.environ.get(env, local_profile().get(key, default))
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip()


def actor_id() -> str:
    return setting("CO_MEMORY_ACTOR_ID", "actor_id")


def timezone_name() -> str:
    return setting("CO_MEMORY_TIMEZONE", "timezone", DEFAULT_TIMEZONE)


@dataclass(frozen=True)
class DeliveryResult:
    event_id: str
    status: str
    detail: str = ""
    outbox: Path | None = None


def vault_root() -> Path:
    value = setting("CO_MEMORY_VAULT_ROOT", "vault_root")
    if not value:
        raise ValueError("No local Vault configured; use a Vault-capable writer for durable dual-writes")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("vault_root must be an absolute path")
    return path


def agent_comemory_root() -> Path:
    directory = setting("CO_MEMORY_AGENT_COMEMORY_DIR", "agent_comemory_dir", DEFAULT_AGENT_COMEMORY_DIR)
    path = Path(directory)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("agent_comemory_dir must be a safe path relative to vault_root")
    return vault_root() / path


def personal_wiki_root() -> Path:
    directory = setting("CO_MEMORY_PERSONAL_WIKI_DIR", "personal_wiki_dir", DEFAULT_PERSONAL_WIKI_DIR)
    path = Path(directory)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("personal_wiki_dir must be a safe path relative to vault_root")
    return vault_root() / path


def agentmemory_url() -> str:
    value = setting("AGENTMEMORY_URL", "agentmemory_url")
    if not value:
        raise ValueError("AGENTMEMORY_URL or agentmemory_url in the profile is required")
    if not value.startswith(("http://", "https://")):
        raise ValueError("AgentMemory URL must start with http:// or https://")
    return value.rstrip("/")


def agentmemory_secret() -> str:
    return os.environ.get("AGENTMEMORY_SECRET", "").strip()


def outbox_path() -> Path:
    return agent_comemory_root() / "00_System" / "Outbox" / "agentmemory-pending.jsonl"


def post_remember(payload: dict[str, Any], timeout: int = 20) -> tuple[bool, str]:
    """Post one observation. Credentials must come from the caller's own environment."""
    secret = agentmemory_secret()
    if not secret:
        return False, "missing-agentmemory-secret"

    payload = dict(payload)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        if "project" not in payload and metadata.get("project"):
            payload["project"] = metadata["project"]
        if "agentId" not in payload:
            actor = metadata.get("actor_id") or metadata.get("from")
            if actor:
                payload["agentId"] = actor
    request = urllib.request.Request(
        f"{agentmemory_url()}/agentmemory/remember",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
            if isinstance(result, dict) and result.get("success") is True and isinstance(result.get("memory"), dict) and result["memory"].get("id"):
                return True, "ok"
            return False, "invalid-or-unsuccessful-response"
    except urllib.error.HTTPError as exc:
        return False, f"http-{exc.code}"
    except urllib.error.URLError as exc:
        return False, f"url-{exc.reason}"
    except Exception as exc:
        return False, type(exc).__name__


def deliver_or_queue(payload: dict[str, Any], event_type: str) -> DeliveryResult:
    """Attempt Layer 1 delivery; persist a retryable outbox event on failure."""
    event_id = uuid.uuid4().hex
    metadata = {**payload.get("metadata", {}), "event_id": event_id, "event_type": event_type}
    enriched = {**payload, "metadata": metadata}
    ok, detail = post_remember(enriched)
    if ok:
        return DeliveryResult(event_id=event_id, status="delivered")

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "last_error": detail,
        "payload": enriched,
    }
    path = outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with outbox_lock(path):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return DeliveryResult(event_id=event_id, status="queued", detail=detail, outbox=path)


def pending_count() -> int:
    path = outbox_path()
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


@contextmanager
def outbox_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        else:
            lock.seek(0)
            if not lock.read(1):
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock, fcntl.LOCK_UN)
            else:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def flush_outbox() -> dict[str, int]:
    """Retry queued events and atomically retain only entries that still fail."""
    path = outbox_path()
    result = {"delivered": 0, "pending": 0, "invalid": 0}
    with outbox_lock(path):
        return _flush_locked(path, result)


def _flush_locked(path: Path, result: dict[str, int]) -> dict[str, int]:
    if not path.exists():
        return result

    remaining: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
                payload = event["payload"]
            except (json.JSONDecodeError, KeyError, TypeError):
                remaining.append(raw)
                result["invalid"] += 1
                continue

            ok, detail = post_remember(payload)
            if ok:
                result["delivered"] += 1
                continue

            event["last_error"] = detail
            remaining.append(json.dumps(event, ensure_ascii=False) + "\n")
            result["pending"] += 1

    if not remaining:
        path.unlink(missing_ok=True)
        return result

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.writelines(remaining)
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return result
