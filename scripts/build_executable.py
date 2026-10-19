"""Build standalone executable using PyInstaller per Section 15.5.

Note: Each operating system must build its own binary (Windows, macOS, Linux).
PyInstaller is not a runtime or test dependency of the C-- project.
"""

from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    """Run PyInstaller build for C--."""
    repo_root = Path(__file__).resolve().parent.parent
    entry_script = repo_root / "scripts" / "entry.py"

    # Check if PyInstaller is available
    pyinstaller_bin = shutil.which("pyinstaller")
    if pyinstaller_bin is None:
        try:
            import PyInstaller  # noqa: F401
            has_pyinstaller = True
        except ImportError:
            has_pyinstaller = False

        if not has_pyinstaller:
            sys.stderr.write(
                "Error: PyInstaller is not installed.\n"
                "Install it with: pip install pyinstaller\n"
                "Note: Standalone executables must be built on their respective target operating systems.\n"
            )
            return 1
        cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--name", "cmm", str(entry_script)]
    else:
        cmd = [pyinstaller_bin, "--onefile", "--name", "cmm", str(entry_script)]

    print(f"Running build command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(repo_root))
    if result.returncode != 0:
        sys.stderr.write(f"PyInstaller build failed with exit code {result.returncode}\n")
        return result.returncode

    ext = ".exe" if sys.platform == "win32" else ""
    binary_path = repo_root / "dist" / f"cmm{ext}"
    print(f"\nStandalone binary built successfully at: {binary_path}")
    print("Note: Each operating system must build its own binary (Windows, macOS, Linux).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
