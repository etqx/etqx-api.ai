import hashlib
import re
from pathlib import Path
from typing import List

SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def ensure_dir_exists(dir_path: Path) -> None:
    if not dir_path.exists():
        raise FileNotFoundError(f"Capabilities directory missing: {dir_path}")


def list_capability_files(dir_path: Path) -> List[Path]:
    ensure_dir_exists(dir_path)
    return sorted(dir_path.glob("*.txt"))


def slug_from_file(path: Path) -> str:
    return path.stem


def validate_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError("invalid id")


def file_for_slug(dir_path: Path, slug: str) -> Path:
    validate_slug(slug)
    p = (dir_path / f"{slug}.txt").resolve()
    # prevent path traversal
    if not str(p).startswith(str(dir_path.resolve())):
        raise ValueError("invalid path")
    return p


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def derive_name(slug: str, text: str) -> str:
    # Use first non-empty line as title if short; otherwise Title Case the slug
    for line in text.splitlines():
        t = line.strip().lstrip("#").strip()
        if t:
            return t if len(t) <= 120 else slug.replace("-", " ").title()
    return slug.replace("-", " ").title()


def file_etag(path: Path) -> str:
    st = path.stat()
    raw = f"{path.name}:{st.st_mtime_ns}:{st.st_size}".encode("utf-8")
    return '"' + hashlib.md5(raw).hexdigest() + '"'

