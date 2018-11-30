__all__ = ("FulfillmentPromise",)

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


class FulfillmentPromise(ChainedPromise[K, L]):
    def __init__(
        self,
        promise: Promise[K],
        on_fulfilled: T.Callable[[K], T.Union[L, T.Awaitable[L]]],
        **kwargs: T.Any,
    ) -> None:
        super().__init__(promise, on_fulfilled, **kwargs)

    async def _wrapper(
        self, promise: T.Awaitable[K], on_fulfilled: T.Callable[[K], T.Union[L, T.Awaitable[L]]]
    ) -> L:
        """Coroutine that wraps a promise and manages a fulfillment callback.

        Arguments:
            promise: Promise to be awaited for chain action
            on_fulfilled: Fulfillment callback.

        Returns:
            Callback result.

        """
        return await attempt_await(on_fulfilled(await promise), self.loop)
