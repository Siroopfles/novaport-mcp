"""Gemeenschappelijke test utilities."""
import shutil
from pathlib import Path
import time
import warnings

def robust_rmtree(path: str | Path, max_retries: int = 3, base_delay: float = 1.0):
    """
    Verwijder een directory met retry mechanisme en exponentiële backoff.
    
    Args:
        path: Het pad om te verwijderen
        max_retries: Maximum aantal pogingen (default: 3)
        base_delay: Basis wachttijd tussen pogingen (default: 1.0)
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
                retry_delay = base_delay * (2 ** attempt)  # Exponentiële backoff
                time.sleep(retry_delay)
            else:
                warnings.warn(
                    f"Kon directory niet verwijderen na {max_retries} pogingen: {path}"
                )