#!/usr/bin/env python3
"""Add ToonSim's shrink-only scaling to the noVNC page installed by apt.

The patch is deliberately small and idempotent. If Debian changes noVNC's
HTML in a way that removes the anchors below, the build fails instead of
silently shipping the old (upscaling) behaviour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/share/novnc")
HTML = ROOT / "vnc.html"
DEFAULTS = ROOT / "defaults.json"
DUTCH_LOCALE = ROOT / "app/locale/nl.json"

SCRIPT_TAG = (
    '<script type="module" crossorigin="anonymous" '
    'src="app/toonsim-downscale.js"></script>'
)
SCRIPT_ANCHOR = (
    '<script type="module" crossorigin="anonymous" '
    'src="app/error-handler.js"></script>'
)

OLD_LABEL = '<option value="scale">Local scaling</option>'
NEW_LABEL = '<option value="scale">Local scaling (shrink only)</option>'


def main() -> int:
    text = HTML.read_text(encoding="utf-8")

    if SCRIPT_TAG not in text:
        if SCRIPT_ANCHOR not in text:
            raise SystemExit(f"{HTML}: noVNC error-handler script tag not found")
        text = text.replace(SCRIPT_ANCHOR, f"{SCRIPT_ANCHOR}\n    {SCRIPT_TAG}", 1)

    if OLD_LABEL in text:
        text = text.replace(OLD_LABEL, NEW_LABEL, 1)

    HTML.write_text(text, encoding="utf-8")

    # Make the shrink-only mode the initial setting without forcing it on
    # every load. A user can still select "None" and have that remembered in
    # noVNC's local settings storage.
    if DEFAULTS.is_file():
        defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    else:
        defaults = {}
    defaults["resize"] = "scale"
    DEFAULTS.write_text(
        json.dumps(defaults, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    # noVNC translates the settings panel from app/locale/*.json. Keep the
    # new option Dutch when the browser uses the Dutch locale.
    if DUTCH_LOCALE.is_file():
        translations = json.loads(DUTCH_LOCALE.read_text(encoding="utf-8"))
        translations["Local scaling (shrink only)"] = (
            "Lokaal schalen (alleen verkleinen)"
        )
        DUTCH_LOCALE.write_text(
            json.dumps(translations, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )

    print(f"Patched {HTML}: noVNC local scaling is now shrink-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
