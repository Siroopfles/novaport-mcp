"""Common test utilities."""

import shutil
import time
import warnings
from pathlib import Path


def robust_rmtree(path: str | Path, max_retries: int = 3, base_delay: float = 1.0):
    """Remove a directory with retry mechanism and exponential backoff.

    Args:
    ----
        path: The path to remove
        max_retries: Maximum number of attempts (default: 3)
        base_delay: Base wait time between attempts (default: 1.0)

    """
    path = Path(path)
    if not path.exists():
        return

    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            break
        except PermissionError:
            if attempt < max_retries - 1:
                retry_delay = base_delay * (2**attempt)  # Exponential backoff
                time.sleep(retry_delay)
            else:
                warnings.warn(
                    f"Could not remove directory after {max_retries} attempts: {path}"
                )
