# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Internal
import sys
import typing as T
from asyncio import Task

# Project
from .chain_link import ChainLink

# Generic types
K = T.TypeVar("K")


class Promise(ChainLink[K], T.ContextManager["Promise[K]"]):
    """An Promise implementation that encapsulate an awaitable."""

    def __enter__(self) -> "Promise[K]":
        return self

    def __exit__(self, exc_type: T.Any, exc_val: T.Any, exc_tb: T.Any) -> None:
        self.cancel()

    def resolve(self, result: K) -> "Promise[K]":
        """Resolve Promise with given value.

        Arguments:
            result: Result to resolve Promise with.

        Raises:
            RuntimeError: Raised when attempting to resolve a Task
            InvalidStateError: Raised when promise was already resolved

        """
        if sys.version_info < (3, 7) and isinstance(self._fut, Task):
            # This is needs to exist because it's incorrectly allowed on Python <= 3.6
            raise RuntimeError("Task does not support set_result operation")

        self._fut.set_result(result)

        return self

    def reject(self, error: T.Union[type, BaseException]) -> "Promise[K]":
        """Reject promise with given value.

        Arguments:
            error: Error to reject Promise with.

        Raises:
            RuntimeError: Raised when attempting to reject a Task
            InvalidStateError: Raised when promise was already resolved

        """
        if sys.version_info < (3, 7) and isinstance(self._fut, Task):
            # This is needs to exist because it's incorrectly allowed on Python < 3.7
            raise RuntimeError("Task does not support set_exception operation")

        self._fut.set_exception(error)

        return self


__all__ = ("Promise",)
