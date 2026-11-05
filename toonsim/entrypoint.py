#!/usr/bin/env python3
"""Home Assistant app entrypoint for ToonSim, including persistent firmware recovery."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

APP_ROOT = Path("/opt/toonsim")
DATA_ROOT = Path("/data/toonsim")
OPTIONS_FILE = Path("/data/options.json")
SHARE_ROOT = Path("/share")
SHARED_APPS_ROOT = SHARE_ROOT / "ToonSim"
SHARED_APPS_DIR = SHARED_APPS_ROOT / "apps"
LEGACY_APPS_DIR = DATA_ROOT / "apps"
APPS_MIGRATION_MARKER = DATA_ROOT / ".apps-share-migrated"
APPS_README = "PUT-YOUR-APPS-HERE.txt"
FIRMWARE_DIR = DATA_ROOT / "firmware"
BACKUP_DIR = DATA_ROOT / "backups"
BACKUP_CURRENT = BACKUP_DIR / "firmware-last-good.tar.gz"
BACKUP_PREVIOUS = BACKUP_DIR / "firmware-previous.tar.gz"
BACKUP_METADATA = BACKUP_DIR / "firmware-last-good.json"
BACKUP_PREVIOUS_METADATA = BACKUP_DIR / "firmware-previous.json"
REQUIRED_FIRMWARE_FILES = (
    "resources-static-base.rcc",
    "drawables-base.rcc",
    "compat.rcc",
)
PROCESSES: list[subprocess.Popen] = []
STOPPING = False


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[ToonSim app] [{timestamp}] {message}", flush=True)


def read_options() -> dict:
    try:
        with OPTIONS_FILE.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        value = {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {OPTIONS_FILE}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("The Home Assistant app options file is not a JSON object")
    return value


def directory_has_apps(path: Path) -> bool:
    """True when an apps folder has an app (a folder or a ToonStore symlink)."""
    try:
        return any(
            item.name != APPS_README and (item.is_dir() or item.is_symlink())
            for item in path.iterdir()
        )
    except OSError:
        return False


def copy_apps_tree(source: Path, target: Path) -> bool:
    """Copy apps, keeping ToonStore's relative version symlinks intact."""
    try:
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
    except (OSError, shutil.Error) as exc:
        log(f"WARNING: could not copy apps from {source} to {target}: {exc}")
        return False
    return True


def ensure_apps_directory() -> Path:
    """Return the apps folder, preferring the HA share so SMB users can edit it.

    Apps used to live in /data/toonsim/apps, which is private to the app. They
    now live in /share/ToonSim/apps, which the Samba NAS app exposes through
    its normal "share" SMB share. The old folder is copied once, and the apps
    bundled in the image are used when neither location has apps yet.
    """
    if not SHARE_ROOT.is_dir():
        log("WARNING: /share is not mounted; apps stay in /data/toonsim/apps and are not visible over SMB")
        LEGACY_APPS_DIR.mkdir(parents=True, exist_ok=True)
        return LEGACY_APPS_DIR

    try:
        SHARED_APPS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log(f"WARNING: cannot create {SHARED_APPS_DIR}: {exc}; apps stay in {LEGACY_APPS_DIR}")
        LEGACY_APPS_DIR.mkdir(parents=True, exist_ok=True)
        return LEGACY_APPS_DIR

    if not APPS_MIGRATION_MARKER.exists():
        initialized = directory_has_apps(SHARED_APPS_DIR)
        if (not initialized
                and LEGACY_APPS_DIR.is_dir()
                and not LEGACY_APPS_DIR.is_symlink()
                and directory_has_apps(LEGACY_APPS_DIR)):
            log(f"Copying existing apps from {LEGACY_APPS_DIR} to {SHARED_APPS_DIR}")
            initialized = copy_apps_tree(LEGACY_APPS_DIR, SHARED_APPS_DIR)
        elif not initialized:
            bundled = APP_ROOT / "apps"
            if bundled.is_dir() and not bundled.is_symlink() and directory_has_apps(bundled):
                log(f"Copying the apps bundled in the image to {SHARED_APPS_DIR}")
                initialized = copy_apps_tree(bundled, SHARED_APPS_DIR)
        if initialized:
            try:
                APPS_MIGRATION_MARKER.write_text(
                    f"Apps are stored in {SHARED_APPS_DIR} since "
                    f"{datetime.now(timezone.utc).isoformat()}\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                log(f"WARNING: cannot write {APPS_MIGRATION_MARKER}: {exc}")

    readme = SHARED_APPS_DIR / APPS_README
    if not readme.exists():
        try:
            readme.write_text(
                "Each app goes in its own folder, as in /qmf/qml/apps on the Toon:\n"
                "  apps/<app>/<App>App.qml\n"
                "Restart the ToonSim app after adding or changing an app.\n",
                encoding="utf-8",
            )
        except OSError as exc:
            log(f"WARNING: cannot write {readme}: {exc}")

    return SHARED_APPS_DIR


def link_app_root(name: str, target: Path) -> None:
    link = APP_ROOT / name
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.exists():
        shutil.rmtree(link)
    link.symlink_to(target, target_is_directory=True)


def ensure_persistent_directories() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    firmware_dir = DATA_ROOT / "firmware"
    data_dir = DATA_ROOT / "data"
    firmware_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    apps_dir = ensure_apps_directory()
    link_app_root("firmware", firmware_dir)
    link_app_root("data", data_dir)
    link_app_root("apps", apps_dir)
    log(f"Apps folder: {apps_dir}")
    if apps_dir == SHARED_APPS_DIR:
        log("Apps are visible in the Samba NAS 'share' SMB share under ToonSim/apps")


def firmware_is_valid(path: Path = FIRMWARE_DIR) -> bool:
    return path.is_dir() and all((path / item).is_file() for item in REQUIRED_FIRMWARE_FILES)


def safe_remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def replace_firmware_directory(candidate: Path) -> None:
    displaced = DATA_ROOT / "firmware-replaced"
    safe_remove(displaced)
    had_old = FIRMWARE_DIR.exists()
    if had_old:
        os.replace(FIRMWARE_DIR, displaced)
    try:
        os.replace(candidate, FIRMWARE_DIR)
    except Exception:
        if had_old and displaced.exists():
            os.replace(displaced, FIRMWARE_DIR)
        raise
    safe_remove(displaced)


def restore_firmware_backup() -> bool:
    for archive_path in (BACKUP_CURRENT, BACKUP_PREVIOUS):
        if not archive_path.is_file():
            continue
        staging = Path(tempfile.mkdtemp(prefix="toonsim-restore-", dir=DATA_ROOT))
        try:
            log(f"Attempting firmware recovery from {archive_path.name}")
            with tarfile.open(archive_path, mode="r:gz") as archive:
                archive.extractall(staging, filter="data")
            candidate = staging / "firmware"
            if not firmware_is_valid(candidate):
                log(f"Backup {archive_path.name} is incomplete or invalid; trying the next snapshot")
                continue
            replace_firmware_directory(candidate)
            if archive_path == BACKUP_PREVIOUS:
                promoted = BACKUP_DIR / "firmware-promoted.tmp.tar.gz"
                shutil.copy2(BACKUP_PREVIOUS, promoted)
                os.replace(promoted, BACKUP_CURRENT)
                if BACKUP_PREVIOUS_METADATA.is_file():
                    shutil.copy2(BACKUP_PREVIOUS_METADATA, BACKUP_METADATA)
                else:
                    BACKUP_METADATA.unlink(missing_ok=True)
            log(f"Firmware successfully restored from {archive_path.name}")
            return True
        except Exception as exc:
            log(f"Could not restore {archive_path.name}: {exc}")
        finally:
            safe_remove(staging)
    return False


def firmware_fingerprint() -> str:
    digest = hashlib.sha256()
    for item in sorted(FIRMWARE_DIR.rglob("*")):
        relative = item.relative_to(FIRMWARE_DIR).as_posix()
        stat = item.lstat()
        digest.update(f"{relative}\0{stat.st_mode}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def read_backup_fingerprint() -> str | None:
    try:
        with BACKUP_METADATA.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return str(data.get("fingerprint", "")) or None
    except (OSError, json.JSONDecodeError, AttributeError):
        return None


def write_json_atomically(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def create_firmware_backup() -> None:
    if not firmware_is_valid():
        raise RuntimeError("Refusing to back up firmware because the required firmware files are missing")

    fingerprint = firmware_fingerprint()
    if BACKUP_CURRENT.is_file() and read_backup_fingerprint() == fingerprint:
        log("Firmware backup is already up to date; no new archive is needed")
        return

    temporary_archive = BACKUP_DIR / "firmware-backup.tmp.tar.gz"
    temporary_archive.unlink(missing_ok=True)
    log("Creating a compressed backup of the current Toon firmware")
    try:
        with tarfile.open(temporary_archive, mode="w:gz", compresslevel=5) as archive:
            archive.add(FIRMWARE_DIR, arcname="firmware")

        if BACKUP_CURRENT.is_file():
            BACKUP_PREVIOUS.unlink(missing_ok=True)
            os.replace(BACKUP_CURRENT, BACKUP_PREVIOUS)
            if BACKUP_METADATA.is_file():
                BACKUP_PREVIOUS_METADATA.unlink(missing_ok=True)
                os.replace(BACKUP_METADATA, BACKUP_PREVIOUS_METADATA)

        os.replace(temporary_archive, BACKUP_CURRENT)
        write_json_atomically(
            BACKUP_METADATA,
            {
                "fingerprint": fingerprint,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": sum(1 for item in FIRMWARE_DIR.rglob("*") if item.is_file()),
            },
        )
        log("Firmware backup saved in /data/toonsim/backups (latest + previous snapshot retained)")
    finally:
        temporary_archive.unlink(missing_ok=True)


def fetch_firmware(options: dict) -> None:
    if firmware_is_valid():
        log("Persistent Toon firmware is present and passed validation; skipping SSH copy")
        return

    log("Persistent firmware is missing or incomplete; trying automatic backup recovery")
    if restore_firmware_backup():
        return

    toon_ip = str(options.get("toon_ip", "")).strip()
    username = str(options.get("toon_username", "root")).strip() or "root"
    password = str(options.get("toon_password", ""))
    if not toon_ip or not password:
        raise RuntimeError(
            "No valid firmware or backup was found. Open Configuration and enter the rooted Toon IP "
            "and SSH password. The password is not written to the log."
        )

    flags: list[str] = []
    if options.get("copy_apps", True):
        flags.append("--apps")
    if options.get("copy_settings", True):
        flags.append("--settings")

    safe_remove(FIRMWARE_DIR)
    FIRMWARE_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "TOONSIM_ADDON_TOON_IP": toon_ip,
            "TOONSIM_ADDON_TOON_USER": username,
            "TOONSIM_ADDON_TOON_PASSWORD": password,
            "TOONSIM_ADDON_PULL_FLAGS": " ".join(flags),
            "DISPLAY": ":0",
        }
    )
    wrapper = r"""
import os, runpy, shlex, sys
script = '/opt/toonsim/tools/pull_firmware.py'
sys.argv = [script, os.environ['TOONSIM_ADDON_TOON_IP'],
            os.environ['TOONSIM_ADDON_TOON_USER'],
            os.environ['TOONSIM_ADDON_TOON_PASSWORD']]
sys.argv.extend(shlex.split(os.environ.get('TOONSIM_ADDON_PULL_FLAGS', '')))
runpy.run_path(script, run_name='__main__')
"""
    log(f"Copying firmware from rooted Toon {toon_ip} through SSH; the physical Toon is read-only")
    try:
        result = subprocess.run(
            [sys.executable, "-c", wrapper],
            cwd=APP_ROOT,
            env=env,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        log("Firmware copy timed out after 5 minutes")
        if restore_firmware_backup():
            return
        raise RuntimeError("Firmware copy timed out and no valid backup could be restored") from exc

    if result.returncode != 0 or not firmware_is_valid():
        log(f"Firmware copy failed (exit status {result.returncode}); trying the saved backup")
        if restore_firmware_backup():
            return
        raise RuntimeError(
            "Firmware copy failed and no valid backup is available. Check the Toon IP, SSH credentials "
            "and SSH access; see the preceding log lines for the underlying error."
        )

    log("Firmware copy completed and passed validation")


def determine_model(options: dict) -> str:
    selected = str(options.get("model", "auto")).lower()
    if selected in ("toon1", "toon2"):
        return selected
    model_file = APP_ROOT / "firmware" / "toon-model.txt"
    if model_file.is_file():
        model = model_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        if model in ("toon1", "toon2"):
            return model
    log("No valid model marker found; defaulting to Toon 1")
    return "toon1"


def spawn(command: Sequence[str], *, env: dict | None = None, cwd: Path | None = None) -> subprocess.Popen:
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd else None,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    PROCESSES.append(process)
    return process


def wait_ready(process: subprocess.Popen, description: str, seconds: float = 8.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"{description} exited during startup with status {code}")
        time.sleep(0.2)


def stop_all(*_args) -> None:
    global STOPPING
    STOPPING = True
    for process in reversed(PROCESSES):
        if process.poll() is None:
            process.terminate()
    for process in reversed(PROCESSES):
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def main() -> int:
    signal.signal(signal.SIGTERM, stop_all)
    signal.signal(signal.SIGINT, stop_all)

    log(f"Starting ToonSim app; Python {sys.version.split()[0]}, container architecture {os.uname().machine}")
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required for safe firmware archive extraction")

    options = read_options()
    ensure_persistent_directories()

    if options.get("restore_firmware_backup", False):
        log("Manual firmware recovery was requested in Configuration")
        if not restore_firmware_backup():
            raise RuntimeError("Manual recovery was requested, but no valid firmware backup was found")
        log("Manual recovery finished. Turn off 'Restore firmware backup' in Configuration now.")

    fetch_firmware(options)
    create_firmware_backup()

    model = determine_model(options)
    width, height = (800, 480) if model == "toon1" else (1024, 600)
    display_env = os.environ.copy()
    display_env.update(
        {
            "DISPLAY": ":0",
            "HOME": str(DATA_ROOT / "home"),
            "XDG_CACHE_HOME": str(DATA_ROOT / "cache"),
            "QT_X11_NO_MITSHM": "1",
            "QT_QUICK_BACKEND": "software",
            "QT_OPENGL": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    Path(display_env["HOME"]).mkdir(parents=True, exist_ok=True)
    Path(display_env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)

    log(f"Starting virtual {model} display at {width}x{height}")
    xvfb = spawn(
        ["Xvfb", ":0", "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp", "-ac"],
        env=display_env,
    )
    wait_ready(xvfb, "Xvfb", 2.0)

    vnc = spawn(
        ["x11vnc", "-display", ":0", "-rfbport", "5900", "-forever", "-shared", "-localhost", "-nopw", "-quiet"],
        env=display_env,
    )
    wait_ready(vnc, "x11vnc", 2.0)
    websocket = spawn(["websockify", "127.0.0.1:6081", "127.0.0.1:5900"], env=display_env)
    wait_ready(websocket, "websockify", 2.0)
    nginx = spawn(["nginx", "-g", "daemon off;"], env=display_env)
    wait_ready(nginx, "nginx", 2.0)

    command = ["/bin/sh", str(APP_ROOT / "toonsim.sh"), "--web-port", "8889"]
    requested_model = str(options.get("model", "auto")).lower()
    if requested_model in ("toon1", "toon2"):
        command.extend(["--size", requested_model])

    log("Launching ToonSim; touchscreen via Home Assistant Ingress, Toon Mobile on port 8888")
    simulator = spawn(command, env=display_env, cwd=APP_ROOT)
    try:
        while not STOPPING:
            code = simulator.poll()
            if code is not None:
                log(f"ToonSim process exited with status {code}")
                return code
            for process, name in (
                (xvfb, "Xvfb"),
                (vnc, "x11vnc"),
                (websocket, "websockify"),
                (nginx, "nginx"),
            ):
                if process.poll() is not None:
                    raise RuntimeError(f"Required service {name} stopped unexpectedly")
            time.sleep(1)
    finally:
        log("Stopping ToonSim services")
        stop_all()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log(f"FATAL: {type(exc).__name__}: {exc}")
        traceback.print_exc(file=sys.stdout)
        stop_all()
        sys.exit(1)
