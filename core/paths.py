from pathlib import Path
import sys

def _detect_root() -> Path:
    """Return project root, handling PyInstaller (_MEIPASS) and source runs."""
    meipass = getattr(sys, "_MEIPASS", None)  # set by PyInstaller at runtime
    if meipass:
        return Path(meipass)
    # running from source: .../core/ -> project root is parent.parent
    return Path(__file__).resolve().parent.parent

ROOTDIR = _detect_root()

def resource_path(*relative: str) -> Path:
    """Locate bundled files relative to ROOTDIR (works in exe and source)."""
    return ROOTDIR.joinpath(*relative)
