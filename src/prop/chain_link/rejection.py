__all__ = ("RejectionPromise",)

# Internal
import typing as T
from asyncio import CancelledError

# Project
from ..chain_promise import ChainLinkPromise
from ..abstract.promise import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class RejectionPromise(ChainLinkPromise[T.Union[K, L], L]):
    def __init__(
        self,
        promise: Promise[L],
        on_reject: T.Callable[[Exception], T.Union[K, T.Awaitable[K]]],
        **kwargs: T.Any,
    ) -> None:
        super().__init__(promise, on_reject, **kwargs)

    async def _wrapper(
        self,
        promise: T.Awaitable[L],
        on_reject: T.Callable[[Exception], T.Union[K, T.Awaitable[K]]],
    ) -> T.Union[L, K]:
        """Coroutine that wraps a promise and manages a rejection callback.

        Arguments:
            promise: Promise to be awaited for chain action
            on_reject: Rejection callback.

        Returns:
            Callback result.

        """
        try:
            return await promise
        except CancelledError:
            raise  # CancelledError must be propagated
        except Exception as exc:
            # Don't retain chain in memory
            del promise

            # Don't allow simple cancellation from this point forward.
            # This avoids the unintended behaviour that happened when a
            # RejectionPromise is cancelled inside it's own on_reject callback
            # and that resulted in the callback also being cancelled
            self._waiting_chain_result = False

            return await self._ensure_chain(on_reject(exc))
