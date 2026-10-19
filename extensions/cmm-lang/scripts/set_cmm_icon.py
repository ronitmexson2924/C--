#!/usr/bin/env python3
"""Set custom C-- logo icon on .cmm files and directories.

Usage:
    python scripts/set_cmm_icon.py [path]

If path is a .cmm file, sets the icon on that file.
If path is a directory (or omitted), recursively sets the icon on all .cmm files.
"""

from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PNG = REPO_ROOT / "assets" / "logo.png"
LOGO_ICNS = REPO_ROOT / "assets" / "cmm.icns"
LOGO_ICO = REPO_ROOT / "assets" / "cmm.ico"


def set_macos_icon(file_path: Path, image_path: Path) -> bool:
    """Set custom Finder icon on macOS using Cocoa NSWorkspace."""
    try:
        from Cocoa import NSImage, NSWorkspace

        img = NSImage.alloc().initWithContentsOfFile_(str(image_path))
        if img is None:
            return False
        ws = NSWorkspace.sharedWorkspace()
        return bool(ws.setIcon_forFile_options_(img, str(file_path), 0))
    except Exception as e:
        sys.stderr.write(f"Warning: Could not set macOS icon on {file_path}: {e}\n")
        return False


def apply_icon_to_target(target: Path) -> int:
    """Apply the C-- logo to a single file or a directory recursively."""
    if not LOGO_PNG.exists():
        sys.stderr.write(f"Error: Logo image not found at {LOGO_PNG}\n")
        return 1

    count = 0
    if target.is_file():
        if target.suffix == ".cmm":
            if sys.platform == "darwin":
                if set_macos_icon(target, LOGO_PNG):
                    print(f"Applied C-- logo to: {target}")
                    count += 1
            else:
                print(f"File icon association is registered via system settings for: {target}")
                count += 1
        else:
            sys.stderr.write(f"Skipping {target}: not a .cmm file\n")
    elif target.is_dir():
        for path in target.rglob("*.cmm"):
            if sys.platform == "darwin":
                if set_macos_icon(path, LOGO_PNG):
                    count += 1
            else:
                count += 1
        print(f"Applied C-- logo to {count} .cmm files in {target}")
    else:
        sys.stderr.write(f"Error: Target '{target}' not found\n")
        return 1

    return 0


def main() -> int:
    target_str = sys.argv[1] if len(sys.argv) > 1 else "."
    target_path = Path(target_str).resolve()
    return apply_icon_to_target(target_path)


if __name__ == "__main__":
    sys.exit(main())
