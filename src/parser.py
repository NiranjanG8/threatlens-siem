import json
import os
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BASE_DIR / "data" / "log_sources.json"


def parse_logs(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_source_config(config_path=DEFAULT_CONFIG_PATH):
    config_file = Path(config_path)
    if config_file.exists():
        with config_file.open() as f:
            config = json.load(f)
        config["_config_dir"] = str(config_file.parent)
        return config

    fallback = {
        "file_sources": [
            {"path": "data/sample_logs.log", "enabled": True, "source": "sample-file"}
        ],
        "windows_event_sources": [
            {"name": "Security", "enabled": False, "max_events": 100}
        ],
    }
    fallback["_config_dir"] = str(BASE_DIR / "data")
    return fallback


def collect_logs(config_path=DEFAULT_CONFIG_PATH):
    config = load_source_config(config_path)
    logs = []
    config_dir = Path(config.get("_config_dir", BASE_DIR))

    for source in config.get("file_sources", []):
        if not source.get("enabled", True):
            continue
        logs.extend(_collect_file_logs(source, config_dir))

    for source in config.get("windows_event_sources", []):
        if not source.get("enabled", True):
            continue
        logs.extend(_collect_windows_events(source))

    return logs


def _collect_file_logs(source, config_dir):
    path = _resolve_source_path(source["path"], config_dir)
    if not path.exists():
        return []

    raw_lines = parse_logs(path)
    source_name = source.get("source", path.name)
    return [
        {"source": source_name, "raw": line, "log_type": "text"}
        for line in raw_lines
    ]


def _resolve_source_path(raw_path, config_dir):
    path = Path(raw_path)
    if path.is_absolute():
        return path

    config_relative = config_dir / path
    if config_relative.exists():
        return config_relative

    return BASE_DIR / path


def _collect_windows_events(source):
    log_name = source.get("name", "Security")
    max_events = int(source.get("max_events", 100))
    powershell = (
        "Get-WinEvent -LogName '{log_name}' -MaxEvents {max_events} | "
        "Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, MachineName, Message | "
        "ConvertTo-Json -Depth 3"
    ).format(log_name=log_name, max_events=max_events)

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        events = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(events, dict):
        events = [events]

    normalized = []
    for event in events:
        normalized.append(
            {
                "source": f"windows:{log_name}",
                "log_type": "windows_event",
                "timestamp": event.get("TimeCreated"),
                "event_id": event.get("Id"),
                "provider": event.get("ProviderName"),
                "level": event.get("LevelDisplayName"),
                "host": event.get("MachineName") or os.environ.get("COMPUTERNAME"),
                "raw": (event.get("Message") or "").strip(),
            }
        )

    return normalized
