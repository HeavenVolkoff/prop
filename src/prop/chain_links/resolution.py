__all__ = ("ResolutionPromise",)

# Internal
import typing as T

# External
from async_tools.attempt_await import attempt_await

# Project
from ..chain_promise import ChainedPromise
from ..abstract.promise import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class ResolutionPromise(ChainedPromise[K, K]):
    def __init__(
        self, promise: Promise[K], on_resolution: T.Callable[[], T.Any], **kwargs: T.Any
    ) -> None:
        super().__init__(promise, on_resolution, **kwargs)

        self._direct_cancellation = False

    def cancel(self) -> bool:
        self._direct_cancellation = True
        return super().cancel()

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
            # Finally executes always, except in the case itself was stopped.
            if not self._direct_cancellation:
                await attempt_await(on_resolution(), self.loop)
