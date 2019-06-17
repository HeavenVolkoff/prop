# Internal
import typing as T
from abc import abstractmethod
from asyncio import FIRST_COMPLETED, CancelledError, wait, shield, Future

# External
from async_tools import attempt_await
from async_tools.abstract import AsyncABCMeta

# Project
from .abstract import Promise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")
M = T.TypeVar("M")


class ChainPromise(T.Generic[K, L], Promise[K], metaclass=AsyncABCMeta):
    """Promise implementation that maintains the callback queue using :class:`~typing.Coroutine`.

    See: :class:`~.abstract.promise.Promise` for more information on the Promise abstract interface.
    """

    def __init__(
        self, promise: Promise[L], callback: T.Callable[..., T.Any], **kwargs: T.Any
    ) -> None:
        if promise.cancelled():
            raise CancelledError("Promise is already cancelled")

        # Ensure correct chain behaviour
        promise.__chain__(self._ensure_chain)

        # Shield promise to allow mid-chain cancellation without causing side-effects for previous links
        super().__init__(self._wrapper(shield(promise, loop=promise.loop), callback), **kwargs)

    def _ensure_chain(self, chain: "Future[T.Any]") -> T.Any:
        if chain.cancelled():
            self.cancel()

    @abstractmethod
    async def _wrapper(self, promise: T.Awaitable[L], callback: T.Callable[..., T.Any]) -> K:
        raise NotImplementedError

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], T.Awaitable[L]]) -> "ChainPromise[L, K]":
        ...

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], L]) -> "ChainPromise[L, K]":
        ...

    def then(self, on_fulfilled: T.Callable[[K], T.Any]) -> "ChainPromise[T.Any, K]":
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
    ) -> "ChainPromise[T.Union[L, K], K]":
        ...

    @T.overload
    def catch(self, on_reject: T.Callable[[Exception], L]) -> "ChainPromise[T.Union[L, K], K]":
        ...

    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> "ChainPromise[T.Any, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if a exception is raised, it will call the callback with the promise
        exception.

        See: :meth:`~.abstract.promise.Promise.catch` for more information.

        """
        from .chain_link import RejectionPromise

        return RejectionPromise(self, on_reject, loop=self._loop)

    def lastly(self, on_resolved: T.Callable[[], T.Any]) -> "ChainPromise[K, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and
        call the callback.

        See: :meth:`~.abstract.promise.Promise.lastly` for more information.

        """
        from .chain_link import ResolutionPromise

        return ResolutionPromise(self, on_resolved, loop=self._loop)


__all__ = ("ChainPromise",)
