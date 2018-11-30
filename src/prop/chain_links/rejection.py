__all__ = ("RejectionPromise",)

# Internal
import typing as T
from asyncio import CancelledError

# External
from async_tools.attempt_await import attempt_await

# Project
from ..chain_promise import ChainedPromise
from ..abstract.promise import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class RejectionPromise(ChainedPromise[K, L]):
    def __init__(
        self,
        promise: Promise[K],
        on_reject: T.Callable[[Exception], T.Union[L, T.Awaitable[L]]],
        **kwargs: T.Any,
    ) -> None:
        super().__init__(promise, on_reject, **kwargs)

    async def _wrapper(
        self,
        promise: T.Awaitable[K],
        on_reject: T.Callable[[Exception], T.Union[L, T.Awaitable[L]]],
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
            return await attempt_await(on_reject(exc), self.loop)
