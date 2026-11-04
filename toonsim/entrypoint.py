#!/usr/bin/env python3
"""Home Assistant app entrypoint for ToonSim."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

APP_ROOT = Path("/opt/toonsim")
DATA_ROOT = Path("/data/toonsim")
OPTIONS_FILE = Path("/data/options.json")
PROCESSES: list[subprocess.Popen] = []
STOPPING = False


def log(message: str) -> None:
    print(f"[ToonSim app] {message}", flush=True)


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


def ensure_persistent_directories() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ("firmware", "data", "apps"):
        target = DATA_ROOT / name
        target.mkdir(parents=True, exist_ok=True)
        link = APP_ROOT / name
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.exists():
            shutil.rmtree(link)
        link.symlink_to(target, target_is_directory=True)


def fetch_firmware(options: dict) -> None:
    firmware_marker = APP_ROOT / "firmware" / "resources-static-base.rcc"
    if firmware_marker.is_file():
        log("Existing Toon firmware found in persistent storage; skipping initial copy")
        return

    toon_ip = str(options.get("toon_ip", "")).strip()
    username = str(options.get("toon_username", "root")).strip() or "root"
    password = str(options.get("toon_password", ""))
    if not toon_ip or not password:
        raise RuntimeError(
            "Toon firmware is not present yet. Open the app Configuration tab and set "
            "toon_ip and toon_password for your rooted Toon, then restart the app."
        )

    flags: list[str] = []
    if options.get("copy_apps", True):
        flags.append("--apps")
    if options.get("copy_settings", True):
        flags.append("--settings")

    # The password is passed through the environment and assembled into sys.argv
    # inside Python, rather than appearing in the process command line.
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
    log(f"Copying firmware from rooted Toon at {toon_ip} via SSH (read-only on the Toon)")
    result = subprocess.run([sys.executable, "-c", wrapper], cwd=APP_ROOT, env=env)
    if result.returncode != 0 or not firmware_marker.is_file():
        raise RuntimeError(
            "Firmware copy failed. Check the Toon IP, SSH credentials and that SSH is enabled on the rooted Toon. "
            "See the app log for the SSH error."
        )
    log("Firmware copied successfully and stored persistently")


def determine_model(options: dict) -> str:
    selected = str(options.get("model", "auto")).lower()
    if selected in ("toon1", "toon2"):
        return selected
    model_file = APP_ROOT / "firmware" / "toon-model.txt"
    if model_file.is_file():
        model = model_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        if model in ("toon1", "toon2"):
            return model
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

    options = read_options()
    ensure_persistent_directories()
    fetch_firmware(options)

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

    log(f"Starting virtual {model} display ({width}x{height})")
    xvfb = spawn(
        ["Xvfb", ":0", "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp", "-ac"],
        env=display_env,
    )
    wait_ready(xvfb, "Xvfb", 2.0)

    # VNC listens only on loopback. It is reachable in the browser solely through
    # the nginx Ingress listener, which allows the Supervisor ingress gateway IP.
    vnc = spawn(
        ["x11vnc", "-display", ":0", "-rfbport", "5900", "-forever", "-shared", "-localhost", "-nopw", "-quiet"],
        env=display_env,
    )
    wait_ready(vnc, "x11vnc", 2.0)

    websocket = spawn(["websockify", "127.0.0.1:6081", "127.0.0.1:5900"], env=display_env)
    wait_ready(websocket, "websockify", 2.0)

    nginx = spawn(["nginx", "-g", "daemon off;"], env=display_env)
    wait_ready(nginx, "nginx", 2.0)

    command = [str(APP_ROOT / "toonsim.sh"), "--web-port", "8889"]
    requested_model = str(options.get("model", "auto")).lower()
    if requested_model in ("toon1", "toon2"):
        command.extend(["--size", requested_model])

    log("Starting ToonSim. The touchscreen is available through Home Assistant Ingress.")
    simulator = spawn(command, env=display_env, cwd=APP_ROOT)
    try:
        while not STOPPING:
            code = simulator.poll()
            if code is not None:
                log(f"ToonSim exited with status {code}")
                return code
            for process, name in ((xvfb, "Xvfb"), (vnc, "x11vnc"), (websocket, "websockify"), (nginx, "nginx")):
                if process.poll() is not None:
                    raise RuntimeError(f"Required service {name} stopped unexpectedly")
            time.sleep(1)
    finally:
        stop_all()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # log a clean failure into the Home Assistant app log
        log(f"FATAL: {exc}")
        stop_all()
        sys.exit(1)
