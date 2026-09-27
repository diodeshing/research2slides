import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_schemas_match_models() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/export_schemas.py", "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

