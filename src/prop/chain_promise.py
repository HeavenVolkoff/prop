# Internal
import typing as T
from abc import abstractmethod
from asyncio import FIRST_COMPLETED, CancelledError, wait, shield

# External
from async_tools import attempt_await
from async_tools.abstract import AsyncABCMeta

# Project
from .abstract import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")
M = T.TypeVar("M")


class ChainPromise(Promise[K]):
    """Promise implementation that maintains the callback queue using :class:`~typing.Coroutine`.

    See: :class:`~.abstract.promise.Promise` for more information on the Promise abstract interface.
    """

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], T.Awaitable[L]]) -> "ChainLinkPromise[L, K]":
        ...  # pragma: no cover

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], L]) -> "ChainLinkPromise[L, K]":
        ...  # pragma: no cover

    def then(self, on_fulfilled: T.Callable[[K], T.Any]) -> "ChainLinkPromise[T.Any, T.Any]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if no exception is raised, it will call the callback with the promise
        result.

        See: :meth:`~.abstract.promise.Promise.then` for more information.

        """
        from .chain_link import FulfillmentPromise

        return FulfillmentPromise(self, on_fulfilled, loop=self._loop)

    @T.overload
    def catch(
        self, on_reject: T.Callable[[Exception], T.Awaitable[L]]
    ) -> "ChainLinkPromise[T.Union[L, K], K]":
        ...  # pragma: no cover

    @T.overload
    def catch(self, on_reject: T.Callable[[Exception], L]) -> "ChainLinkPromise[T.Union[L, K], K]":
        ...  # pragma: no cover

    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> "ChainLinkPromise[T.Any, T.Any]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if a exception is raised, it will call the callback with the promise
        exception.

        See: :meth:`~.abstract.promise.Promise.catch` for more information.

        """
        from .chain_link import RejectionPromise

        return RejectionPromise(self, on_reject, loop=self._loop)

    def lastly(self, on_resolved: T.Callable[[], T.Any]) -> "ChainLinkPromise[K, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and
        call the callback.

        See: :meth:`~.abstract.promise.Promise.lastly` for more information.

        """
        from .chain_link import ResolutionPromise

        return ResolutionPromise(self, on_resolved, loop=self._loop)


class ChainLinkPromise(T.Generic[K, L], ChainPromise[K], metaclass=AsyncABCMeta):
    """A special promise implementation used by the chained callback Promises."""

    def __init__(
        self, promise: Promise[L], callback: T.Callable[..., T.Any], **kwargs: T.Any
    ) -> None:
        super().__init__(self._wrapper(shield(promise, loop=promise.loop), callback), **kwargs)

        # Internal
        self._parent_notify_chain = promise.notify_chain
        self._waiting_chain_result = True  # Flag for controlling cancellation

    @T.overload
    async def _ensure_chain(self, result: T.Awaitable[M]) -> M:
        ...  # pragma: no cover

    @T.overload
    async def _ensure_chain(self, result: M) -> M:
        ...  # pragma: no cover

    async def _ensure_chain(self, result: T.Any) -> T.Any:
        task = self.loop.create_task(attempt_await(result, self.loop))

        try:
            await wait((task, self._parent_notify_chain), return_when=FIRST_COMPLETED)
        except CancelledError:
            # Edge case when cancellation is raised during wait call.
            # Ignore it because wait don't propagate CancelledError to it's
            # future, and we take care of everything down below
            pass

        if task.done():
            if self._parent_notify_chain.cancelled():
                # Rearm chain cancellation in the case the result was received
                # but the chain was cancelled instants later.
                # Common case when task is synchronous
                self.notify_chain.cancel()
            else:
                # Solve edge case where a link is added to the chain after it
                # was over. Without this notify_chain wouldn't listen the
                # parent's request for chain cancellation
                self._parent_notify_chain.add_done_callback(lambda _: self.notify_chain.cancel())
        else:
            task.cancel()

        return await task

    def cancel(self, *, task: bool = True, chain: bool = False) -> bool:
        if self._waiting_chain_result or task:
            return super().cancel(chain=chain)

        return False

    @abstractmethod
    async def _wrapper(self, promise: T.Awaitable[L], callback: T.Callable[..., T.Any]) -> K:
        raise NotImplementedError


__all__ = ("ChainPromise", "ChainLinkPromise")
