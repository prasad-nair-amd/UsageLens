"""FastAPI app: serves the static frontend and the host/usage JSON API."""

import asyncio
import json
import logging
import os
import queue
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional

from . import analytics, storage
from .collector import collect_and_store, collect_for_host, DEFAULT_COMMANDS
from .ssh_client import connect, _connect_direct, run_command, test_jump_alias, SSHConnectError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

logger = logging.getLogger("usagelens")

app = FastAPI(title="UsageLens")

# host_id -> running asyncio.Task for its auto-poll loop
POLL_TASKS = {}


class HostIn(BaseModel):
    id: Optional[str] = None
    name: str
    hostname: str
    port: int = 22
    username: str
    auth_method: str = Field("identity_file", pattern="^(identity_file|password)$")
    identity_file: Optional[str] = None
    identity_passphrase: Optional[str] = None
    password: Optional[str] = None
    access_mode: str = Field("direct", pattern="^(direct|jump_host|slurm)$")
    jump_hostname: Optional[str] = None
    jump_port: int = 22
    jump_username: Optional[str] = None
    jump_auth_method: str = Field("identity_file", pattern="^(identity_file|password)$")
    jump_identity_file: Optional[str] = None
    jump_password: Optional[str] = None
    jump_alias: Optional[str] = None
    slurm_hostname: Optional[str] = None
    slurm_port: int = 22
    slurm_username: Optional[str] = None
    slurm_auth_method: str = Field("identity_file", pattern="^(identity_file|password)$")
    slurm_identity_file: Optional[str] = None
    slurm_password: Optional[str] = None
    slurm_salloc_cmd: Optional[str] = None
    slurm_setup_commands: List[str] = Field(default_factory=list)
    commands: List[str] = Field(default_factory=lambda: list(DEFAULT_COMMANDS))
    poll_interval_seconds: int = 300
    auto_poll_enabled: bool = False


class AutoPollIn(BaseModel):
    enabled: bool


def _public_host(host):
    """Strip secrets before sending a host config to the browser."""
    h = dict(host)
    h.pop("password", None)
    h.pop("identity_passphrase", None)
    h.pop("jump_password", None)
    h.pop("slurm_password", None)
    h["has_password"] = bool(host.get("password"))
    h["has_jump_password"] = bool(host.get("jump_password"))
    h["has_slurm_password"] = bool(host.get("slurm_password"))
    return h


def _find_host_cfg(host_id):
    return next((h for h in storage.load_hosts()["hosts"] if h["id"] == host_id), None)


async def _poll_loop(host_id):
    loop = asyncio.get_running_loop()
    while True:
        host_cfg = _find_host_cfg(host_id)
        if host_cfg is None or not host_cfg.get("auto_poll_enabled"):
            return
        try:
            await loop.run_in_executor(None, collect_and_store, host_id)
        except Exception:
            logger.exception("Auto-poll collection failed for host %s", host_id)
        # re-read interval each cycle so a live edit takes effect without restarting
        host_cfg = _find_host_cfg(host_id)
        interval = (host_cfg or {}).get("poll_interval_seconds") or 300
        await asyncio.sleep(max(10, interval))


def _start_poll(host_id):
    if host_id in POLL_TASKS and not POLL_TASKS[host_id].done():
        return
    POLL_TASKS[host_id] = asyncio.create_task(_poll_loop(host_id))


def _stop_poll(host_id):
    task = POLL_TASKS.pop(host_id, None)
    if task is not None and not task.done():
        task.cancel()


@app.on_event("startup")
async def _startup():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, analytics._cached_usage)
    data = storage.load_hosts()

    # Resume auto-polling
    for host in data["hosts"]:
        if host.get("auto_poll_enabled"):
            _start_poll(host["id"])


@app.get("/api/hosts")
def list_hosts():
    hosts = storage.load_hosts()["hosts"]
    return {"hosts": [_public_host(h) for h in hosts]}


@app.post("/api/hosts")
async def upsert_host(host: HostIn):
    data = storage.load_hosts()
    hosts = data["hosts"]
    payload = host.dict()

    if payload.get("id"):
        for i, existing in enumerate(hosts):
            if existing["id"] == payload["id"]:
                if not payload.get("password") and existing.get("password"):
                    payload["password"] = existing["password"]
                if not payload.get("identity_passphrase") and existing.get("identity_passphrase"):
                    payload["identity_passphrase"] = existing["identity_passphrase"]
                if not payload.get("jump_password") and existing.get("jump_password"):
                    payload["jump_password"] = existing["jump_password"]
                if not payload.get("slurm_password") and existing.get("slurm_password"):
                    payload["slurm_password"] = existing["slurm_password"]
                hosts[i] = payload
                break
        else:
            hosts.append(payload)
    else:
        payload["id"] = str(uuid.uuid4())
        hosts.append(payload)

    storage.save_hosts({"hosts": hosts})

    if payload.get("auto_poll_enabled"):
        _start_poll(payload["id"])
    else:
        _stop_poll(payload["id"])

    return _public_host(payload)


@app.delete("/api/hosts/{host_id}")
async def delete_host(host_id: str, background_tasks: BackgroundTasks = None):
    _stop_poll(host_id)
    data = storage.load_hosts()
    hosts = [h for h in data["hosts"] if h["id"] != host_id]
    storage.save_hosts({"hosts": hosts})
    usage_data, removed = analytics.delete_host_from_cache(host_id)
    if removed:
        if background_tasks:
            background_tasks.add_task(storage.save_usage, usage_data)
        else:
            storage.save_usage(usage_data)
    return {"ok": True, "snapshots_removed": removed}


def _get_host_or_404(host_id):
    hosts = storage.load_hosts()["hosts"]
    for h in hosts:
        if h["id"] == host_id:
            return h, hosts
    raise HTTPException(status_code=404, detail="Host not found")


def _effective_access_mode(host_cfg):
    """Determine access mode, supporting old jump_enabled field."""
    mode = host_cfg.get("access_mode")
    if mode and mode != "direct":
        return mode
    if host_cfg.get("jump_enabled") and host_cfg.get("jump_hostname"):
        return "jump_host"
    return mode or "direct"


def _build_jump_cfg(host_cfg):
    """Build a jump host config dict from inline jump_* fields, or None."""
    if _effective_access_mode(host_cfg) != "jump_host" or not host_cfg.get("jump_hostname"):
        return None
    return {
        "hostname": host_cfg["jump_hostname"],
        "port": host_cfg.get("jump_port") or 22,
        "username": host_cfg.get("jump_username") or "",
        "auth_method": host_cfg.get("jump_auth_method") or "identity_file",
        "identity_file": host_cfg.get("jump_identity_file"),
        "password": host_cfg.get("jump_password"),
    }


def _build_slurm_cfg(host_cfg):
    """For Slurm mode, use the main host connection fields as the controller."""
    if _effective_access_mode(host_cfg) != "slurm":
        return None
    return {
        "hostname": host_cfg["hostname"],
        "port": host_cfg.get("port") or 22,
        "username": host_cfg.get("username") or "",
        "auth_method": host_cfg.get("auth_method") or "identity_file",
        "identity_file": host_cfg.get("identity_file"),
        "password": host_cfg.get("password"),
    }


@app.post("/api/hosts/{host_id}/test")
def test_host(host_id: str):
    host_cfg, hosts = _get_host_or_404(host_id)
    mode = _effective_access_mode(host_cfg)

    client = jump_client = None
    try:
        if mode == "slurm":
            slurm_cfg = _build_slurm_cfg(host_cfg)
            if not slurm_cfg:
                return {"ok": False, "message": "Slurm controller not configured"}
            client = _connect_direct(slurm_cfg)
            salloc_cmd = host_cfg.get("slurm_salloc_cmd", "")
            if salloc_cmd:
                # Try with --immediate to avoid hanging if node is busy
                test_cmd = salloc_cmd.rstrip()
                if "--immediate" not in test_cmd:
                    test_cmd += " --immediate"
                exit_code, out, err = run_command(client, f"{test_cmd} bash -c 'echo SLURM_OK; hostname'", timeout=30)
                if exit_code != 0 or "SLURM_OK" not in out:
                    detail = err.strip() or out.strip() or f"exit code {exit_code}"
                    if "busy" in detail.lower() or "unable to allocate" in detail.lower():
                        return {"ok": False, "message": f"SSH to controller OK, but the node is currently busy (allocated by another user). Try again later."}
                    return {"ok": False, "message": f"SSH to controller OK, but salloc failed: {detail}"}
                node_name = out.replace("SLURM_OK", "").strip().split("\n")[-1].strip()
                return {"ok": True, "message": f"Connected to Slurm controller and allocated node ({node_name}) successfully"}
            return {"ok": True, "message": "Connected to Slurm controller"}
        else:
            jump_cfg = _build_jump_cfg(host_cfg)
            client, jump_client = connect(host_cfg, jump_host_cfg=jump_cfg)
            jump_alias = host_cfg.get("jump_alias")
            if jump_cfg and jump_alias:
                test_jump_alias(client, jump_alias)
        return {"ok": True, "message": "Connected successfully"}
    except SSHConnectError as exc:
        return {"ok": False, "message": str(exc)}
    finally:
        if client is not None:
            client.close()
        if jump_client is not None:
            jump_client.close()


@app.post("/api/hosts/{host_id}/collect")
def collect_host(host_id: str):
    _get_host_or_404(host_id)
    snapshot = collect_and_store(host_id)
    return snapshot


@app.get("/api/hosts/{host_id}/collect-stream")
async def collect_host_stream(host_id: str):
    """SSE endpoint that streams collection progress, then the final snapshot."""
    _get_host_or_404(host_id)
    progress_q = queue.Queue()

    def on_progress(step, total, msg):
        progress_q.put({"event": "progress", "step": step, "total": total, "message": msg})

    loop = asyncio.get_running_loop()

    async def event_generator():
        def do_collect():
            hosts = storage.load_hosts()["hosts"]
            host_cfg = next(h for h in hosts if h["id"] == host_id)
            snapshot = collect_for_host(host_cfg, hosts, on_progress=on_progress)
            storage.append_snapshot(snapshot)
            analytics.append_to_cache(snapshot)
            return snapshot

        collect_future = loop.run_in_executor(None, do_collect)

        while not collect_future.done():
            try:
                item = progress_q.get(timeout=0.15)
                yield {"event": "progress", "data": json.dumps(item)}
            except queue.Empty:
                pass
            await asyncio.sleep(0.05)

        snapshot = await collect_future

        while not progress_q.empty():
            item = progress_q.get_nowait()
            yield {"event": "progress", "data": json.dumps(item)}

        yield {"event": "done", "data": json.dumps(snapshot)}

    return EventSourceResponse(event_generator())


@app.post("/api/hosts/{host_id}/autopoll")
async def set_autopoll(host_id: str, body: AutoPollIn):
    data = storage.load_hosts()
    hosts = data["hosts"]
    host_cfg = next((h for h in hosts if h["id"] == host_id), None)
    if host_cfg is None:
        raise HTTPException(status_code=404, detail="Host not found")

    host_cfg["auto_poll_enabled"] = body.enabled
    storage.save_hosts({"hosts": hosts})

    if body.enabled:
        _start_poll(host_id)
    else:
        _stop_poll(host_id)

    return {"ok": True, "auto_poll_enabled": body.enabled}


@app.get("/api/dashboard")
def get_dashboard(range: str = "7d"):
    """Per-host usage summary for the landing page."""
    if range not in analytics.RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Invalid range '{range}'.")
    all_hosts = storage.load_hosts()["hosts"]
    result = []
    for h in all_hosts:
        summary = analytics.dashboard_summary(h["id"], range)
        result.append({
            "host_id": h["id"],
            "name": h.get("name", h["hostname"]),
            "hostname": h["hostname"],
            "snapshot_count": summary["snapshot_count"],
            "distinct_users": summary["distinct_users"],
            "user_summary": summary["user_summary"],
            "total_hours": summary["used_hours"],
            "total_hours_in_range": summary["total_hours_in_range"],
            "used_hours": summary["used_hours"],
            "idle_hours": summary["idle_hours"],
            "last_collected": summary["last_collected"],
            "range_start": summary["range_start"],
            "range_end": summary["range_end"],
        })
    return {"hosts": result}


@app.get("/api/hosts/{host_id}/history")
def get_history(host_id: str, range: str = "7d"):
    _get_host_or_404(host_id)
    if range not in analytics.RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Invalid range '{range}'. Use one of {list(analytics.RANGE_DAYS)}")
    return analytics.build_history(host_id, range)


@app.get("/api/hosts/{host_id}/snapshots")
def list_snapshots(host_id: str):
    _get_host_or_404(host_id)
    return {"snapshots": analytics.list_snapshots(host_id)}


@app.get("/api/hosts/{host_id}/snapshot/{collected_at}")
def get_snapshot_detail(host_id: str, collected_at: str):
    _get_host_or_404(host_id)
    detail = analytics.get_snapshot_detail(host_id, collected_at)
    if detail is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return detail


@app.delete("/api/hosts/{host_id}/snapshot/{collected_at}")
def delete_snapshot(host_id: str, collected_at: str, background_tasks: BackgroundTasks = None):
    _get_host_or_404(host_id)
    data, deleted = analytics.delete_from_cache(host_id, collected_at)
    if not deleted:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    if background_tasks:
        background_tasks.add_task(storage.save_usage, data)
    else:
        storage.save_usage(data)
    return {"ok": True}


@app.get("/api/usage")
def get_usage():
    return storage.load_usage()


@app.get("/api/snapshot-counts")
def get_snapshot_counts():
    """Return {host_id: count} via fast line scan — no full YAML parse."""
    return storage.snapshot_counts()


# Static frontend last, so /api/* routes above take precedence.
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
