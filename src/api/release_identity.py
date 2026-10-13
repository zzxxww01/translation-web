"""Immutable process identity; never follow a moving release pointer per request."""
from pathlib import Path
import re
import subprocess
from uuid import uuid4


def read_revision(root: Path) -> str | None:
    try:
        revision = subprocess.check_output(
            ['git', '-C', str(root.resolve()), 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL, timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return revision if re.fullmatch(r'[0-9a-f]{40}', revision) else None


# Loaded once with this process, not read from frontend metadata or an env override.
REVISION = read_revision(Path(__file__).resolve().parents[2])
INSTANCE_ID = uuid4().hex


def release_identity() -> dict[str, str | None]:
    return {'revision': REVISION, 'instance_id': INSTANCE_ID}
