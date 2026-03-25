import re
from pathlib import Path

import httpx


def safe_attachment_dest(output_dir: Path, page_id: str, filename: str) -> Path:
    """Return a safe destination path under output_dir, guarding against path traversal.

    Attacks neutralised:
    - Absolute paths (e.g. /etc/passwd) → Path.name strips the directory
    - Directory traversal (e.g. ../../.bashrc) → Path.name keeps only the basename
    - Null bytes / control characters → stripped
    - Degenerate names (. / ..) → replaced with "attachment"
    - page_id containing separators → sanitised
    - Final resolved path verified to be inside output_dir (defense-in-depth)
    """
    # 1. Strip to basename — neutralises absolute paths and ../
    basename = Path(filename).name
    # 2. Remove null bytes and control characters
    basename = re.sub(r"[\x00-\x1f\x7f]", "", basename)
    # 3. Reject degenerate names
    if not basename or basename in (".", ".."):
        basename = "attachment"

    # 4. Sanitise page_id (strip path separators; IDs from API are numeric but defence-in-depth)
    safe_id = re.sub(r"[/\\]", "_", page_id)
    if safe_id in (".", "..") or not safe_id:
        safe_id = "_"

    dest = (output_dir / safe_id / basename).resolve()

    # 5. Final guard: verify the resolved path is strictly inside output_dir
    if not dest.is_relative_to(output_dir.resolve()):
        raise ValueError(f"Path traversal detected for attachment: {filename!r}")

    return dest


def download_file(http_client: httpx.Client, url: str, dest: Path) -> None:
    """Stream-download *url* to *dest*, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with http_client.stream("GET", url) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                if chunk:
                    f.write(chunk)
