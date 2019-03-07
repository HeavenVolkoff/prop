__all__ = ("FulfillmentPromise",)

# Internal
import typing as T

# Project
from ..chain_promise import ChainLinkPromise
from ..abstract.promise import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class FulfillmentPromise(ChainLinkPromise[K, L]):
    @T.overload
    def __init__(
        self, promise: Promise[L], on_fulfilled: T.Callable[[L], T.Awaitable[K]], **kwargs: T.Any
    ) -> None:
        ...

    @T.overload
    def __init__(
        self, promise: Promise[L], on_fulfilled: T.Callable[[L], K], **kwargs: T.Any
    ) -> None:
        ...

    def __init__(
        self, promise: Promise[L], on_fulfilled: T.Callable[[L], T.Any], **kwargs: T.Any
    ) -> None:
        super().__init__(promise, on_fulfilled, **kwargs)

    @T.overload
    async def _wrapper(
        self, promise: T.Awaitable[L], on_fulfilled: T.Callable[[L], T.Awaitable[K]]
    ) -> K:
        ...

    @T.overload
    async def _wrapper(self, promise: T.Awaitable[L], on_fulfilled: T.Callable[[L], K]) -> K:
        ...

    async def _wrapper(
        self, promise: T.Awaitable[L], on_fulfilled: T.Callable[[L], T.Union[K, T.Awaitable[K]]]
    ) -> K:
        """Coroutine that wraps a promise and manages a fulfillment callback.

        Arguments:
            promise: Promise to be awaited for chain action
            on_fulfilled: Fulfillment callback.

        Returns:
            Callback result.

        """
        result = await promise

        # Don't retain chain in memory
        del promise

        # Don't allow simple cancellation from this point forward.
        # This avoids the unintended behaviour that happened when a
        # FulfillmentPromise is cancelled inside it's own on_fulfilled
        # callback and that resulted in the callback also being cancelled
        self._waiting_chain_result = False

        return await self._ensure_chain(on_fulfilled(result))
