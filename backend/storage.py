"""Load/save helpers for data files, with file locking so the
web server and a headless `collector.py --all` cron run can't corrupt each other.

Usage data is stored as JSON (fast parsing). Host config stays YAML (small, human-editable).
"""

import json
import os
import yaml
from filelock import FileLock

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HOSTS_FILE = os.path.join(DATA_DIR, "hosts.yaml")
USAGE_FILE = os.path.join(DATA_DIR, "usage_data.json")
USAGE_FILE_YAML = os.path.join(DATA_DIR, "usage_data.yaml")

os.makedirs(DATA_DIR, exist_ok=True)


def _lock_for(path):
    return FileLock(path + ".lock")


# ========== Hosts (YAML — small, human-editable) ==========

def _load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else default


def _save_yaml(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    os.replace(tmp_path, path)


def load_hosts():
    with _lock_for(HOSTS_FILE):
        return _load_yaml(HOSTS_FILE, {"hosts": []})


def save_hosts(data):
    with _lock_for(HOSTS_FILE):
        _save_yaml(HOSTS_FILE, data)


# ========== Usage data (JSON — fast parsing) ==========

def _migrate_yaml_to_json():
    """One-time migration: convert usage_data.yaml to usage_data.json."""
    if os.path.exists(USAGE_FILE_YAML) and not os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE_YAML, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "snapshots" in data:
                with open(USAGE_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                os.rename(USAGE_FILE_YAML, USAGE_FILE_YAML + ".bak")
                return True
        except Exception:
            pass
    return False


def load_usage():
    with _lock_for(USAGE_FILE):
        _migrate_yaml_to_json()
        if not os.path.exists(USAGE_FILE):
            return {"snapshots": []}
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data else {"snapshots": []}


def save_usage(data):
    with _lock_for(USAGE_FILE):
        tmp_path = USAGE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, USAGE_FILE)


def append_snapshot(snapshot):
    """Append a snapshot to the JSON file."""
    with _lock_for(USAGE_FILE):
        _migrate_yaml_to_json()
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"snapshots": []}
        data["snapshots"].append(snapshot)
        tmp_path = USAGE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, USAGE_FILE)
    return snapshot


def snapshot_counts():
    """Count snapshots per host — fast with JSON."""
    data = load_usage()
    counts = {}
    for s in data.get("snapshots", []):
        hid = s.get("host_id", "")
        counts[hid] = counts.get(hid, 0) + 1
    return counts
