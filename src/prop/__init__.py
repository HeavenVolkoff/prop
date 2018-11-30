"""Asynchronous Reactive eXtensions."""

__all__ = ("__version__", "Promise", "ChainPromise", "AbstractPromise")

# External
import pkg_resources

# Project
from .promise import Promise
from .chain_promise import ChainPromise
from .abstract.promise import Promise as AbstractPromise

try:
    __version__ = str(
        pkg_resources.resource_string(__name__, "VERSION"), encoding="utf8"  # type: ignore
    )
except pkg_resources.ResolutionError:
    __version__ = "0.0a0"
