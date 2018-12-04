__all__ = ("ResolutionPromise",)

# Internal
import typing as T

# Project
from ..chain_promise import ChainLinkPromise
from ..abstract.promise import AbstractPromise

# Generic types
K = T.TypeVar("K")


class ResolutionPromise(ChainLinkPromise[K, K]):
    def __init__(
        self, promise: AbstractPromise[K], on_resolution: T.Callable[[], T.Any], **kwargs: T.Any
    ) -> None:
        super().__init__(promise, on_resolution, **kwargs)

        # Internal
        self._direct_cancellation = False  # Flag for identifying when link was directly cancelled

    def cancel(self, *, task: bool = True, chain: bool = False) -> bool:
        self._direct_cancellation = True
        return super().cancel(task=task, chain=chain)

    async def _wrapper(self, promise: T.Awaitable[K], on_resolution: T.Callable[[], T.Any]) -> K:
        """Coroutine that wraps a promise and manages a resolution callback.

        Arguments:
            promise: Promise to be awaited for chain action
            on_resolution: Resolution callback.

        Returns:
            Callback result.

        """
        try:
            return await promise
        finally:
            # Don't retain chain in memory
            del promise

            # Don't allow simple cancellation from this point forward.
            # This avoids the unintended behaviour that happened when a
            # ResolutionPromise is cancelled inside it's own on_resolution
            # callback and that resulted in the callback also being cancelled
            self._waiting_chain_result = False

            # Finally executes always, except in the case itself was stopped.
            if not self._direct_cancellation:
                await self._ensure_chain(on_resolution())
