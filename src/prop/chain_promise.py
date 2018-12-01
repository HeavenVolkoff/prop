__all__ = ("ChainPromise", "ChainedPromise")

# Internal
import typing as T
from abc import ABCMeta, abstractmethod
from asyncio import shield

# Project
from .abstract.promise import Promise as AbstractPromise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class ChainPromise(AbstractPromise[K]):
    """Promise implementation that maintains the callback queue using :class:`~typing.Coroutine`.

    See: :class:`~.abstract.promise.Promise` for more information on the Promise abstract interface.
    """

    def then(
        self, on_fulfilled: T.Callable[[K], T.Union[L, T.Awaitable[L]]]
    ) -> "ChainedPromise[K, L]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if no exception is raised, it will call the callback with the promise
        result.

        See: :meth:`~.abstract.promise.Promise.then` for more information.

        """
        from .chain_links.fulfillment import FulfillmentPromise

        return FulfillmentPromise(self, on_fulfilled, loop=self._loop)

    def catch(
        self, on_reject: T.Callable[[Exception], T.Union[L, T.Awaitable[L]]]
    ) -> "ChainedPromise[K, L]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if a exception is raised, it will call the callback with the promise
        exception.

        See: :meth:`~.abstract.promise.Promise.catch` for more information.

        """
        from .chain_links.rejection import RejectionPromise

        return RejectionPromise(self, on_reject, loop=self._loop)

    def lastly(self, on_resolved: T.Callable[[], T.Any]) -> "ChainedPromise[K, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and
        call the callback.

        See: :meth:`~.abstract.promise.Promise.lastly` for more information.

        """
        from .chain_links.resolution import ResolutionPromise

        return ResolutionPromise(self, on_resolved, loop=self._loop)


class ChainedPromise(T.Generic[K, L], ChainPromise[K], metaclass=ABCMeta):
    """A special promise implementation used by the chained callback Promises."""

    def __init__(
        self, promise: AbstractPromise[K], callback: T.Callable[..., T.Any], **kwargs: T.Any
    ) -> None:
        super().__init__(self._wrapper(shield(promise, loop=promise.loop), callback), **kwargs)

        # Disable the "destroy pending task" warning
        self._fut._log_destroy_pending = False  # type: ignore

        # Flag for controlling cancellation
        self._can_cancel = True

    def cancel(self, *, force: bool = False) -> bool:
        if force or self._can_cancel:
            return super().cancel()

        return False

    @abstractmethod
    def _wrapper(self, promise: T.Awaitable[K], callback: T.Callable[..., T.Any]) -> T.Any:
        raise NotImplementedError
