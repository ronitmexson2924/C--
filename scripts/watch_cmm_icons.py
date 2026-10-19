#!/usr/bin/env python3
"""Background watcher that automatically stamps the C-- logo icon whenever a .cmm file is saved.

Usage:
    python scripts/watch_cmm_icons.py [directory_to_watch]

Runs indefinitely, monitoring the directory for newly created or saved .cmm files.
"""

from pathlib import Path
import os
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PNG = REPO_ROOT / "assets" / "logo.png"


def set_macos_icon(file_path: Path, image_path: Path) -> bool:
    """Set custom Finder icon on macOS using Cocoa NSWorkspace."""
    try:
        from Cocoa import NSImage, NSWorkspace

        img = NSImage.alloc().initWithContentsOfFile_(str(image_path))
        if img is None:
            return False
        ws = NSWorkspace.sharedWorkspace()
        return bool(ws.setIcon_forFile_options_(img, str(file_path), 0))
    except Exception:
        return False


def watch_directory(watch_path: Path, interval: float = 1.0) -> None:
    """Continuously poll for modified or newly saved .cmm files and stamp the logo."""
    print(f"[*] C-- Icon Watcher active. Monitoring: {watch_path}")
    print("[*] Any .cmm file created or saved will automatically receive the C-- logo.")
    print("[*] Press Ctrl+C to stop.")

    known_mtimes: dict[str, float] = {}

    # Initial stamp of existing files
    for p in watch_path.rglob("*.cmm"):
        try:
            mtime = p.stat().st_mtime
            known_mtimes[str(p)] = mtime
            set_macos_icon(p, LOGO_PNG)
        except OSError:
            pass

    try:
        while True:
            time.sleep(interval)
            for p in watch_path.rglob("*.cmm"):
                try:
                    mtime = p.stat().st_mtime
                    path_str = str(p)
                    if path_str not in known_mtimes or known_mtimes[path_str] != mtime:
                        known_mtimes[path_str] = mtime
                        if set_macos_icon(p, LOGO_PNG):
                            print(f"[+] Stamped C-- logo on saved file: {p.name} ({p})")
                except OSError:
                    continue
    except KeyboardInterrupt:
        print("\n[*] C-- Icon Watcher stopped.")


def main() -> int:
    target_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
    watch_directory(target_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
