"""Asynchronous Reactive eXtensions."""

__all__ = ("__version__", "Promise", "ChainPromise")

# External
import pkg_resources

# Project
from .promise import Promise
from .chain_promise import ChainPromise

try:
    __version__ = str(pkg_resources.resource_string(__name__, "VERSION"), encoding="utf8")
except pkg_resources.ResolutionError:  # pragma: no cover
    __version__ = "0.0a0"
