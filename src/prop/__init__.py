# External
from importlib_metadata import version

# Project
from .promise import Promise

try:
    __version__ = version(__name__)
except Exception:
    import traceback
    from warnings import warn

    warn(f"Failed to set version due to:\n{traceback.format_exc()}", ImportWarning)
    __version__ = "0.0a0"

__all__ = ("__version__", "Promise")
