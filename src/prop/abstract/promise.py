# Internal
import sys
import typing as T
from abc import ABCMeta, abstractmethod
from asyncio import Task, Future, Handle, AbstractEventLoop, isfuture, ensure_future

# External
from enum import auto, IntEnum, unique
from functools import partial

import typing_extensions as Te
from async_tools import Loopable
from async_tools.abstract import Loopable as AbstractLoopable, BasicRepr

# Generic types
K = T.TypeVar("K")


@unique
class ChainTypes(IntEnum):
    REJECTION = auto()
    RESOLUTION = auto()
    FULFILLMENT = auto()


class Promise(Loopable, T.Awaitable[K], metaclass=ABCMeta):
    """An abstract Promise implementation that encapsulate an awaitable.

    .. Warning::

        This class is abstract in the sense that no implementation is made as to
        how the callback chain is generated or maintained.
    """

    def __init__(
        self,
        awaitable: T.Optional[T.Awaitable[K]] = None,
        *,
        loop: T.Optional[AbstractEventLoop] = None,
        log_unexpected_exception: bool = True,
        **kwargs: T.Any,
    ) -> None:
        """Promise constructor.

        Arguments:
            awaitable: The awaitable object to be encapsulated.
            loop: Current asyncio loop.
            log_unexpected_exception: Flag for controlling whether errors raised
                in not awaited promises should be logged.
            kwargs: Keyword parameters for super.

        """
        if loop is None:
            # Retrieve loop from awaitable if available
            if isinstance(awaitable, AbstractLoopable):
                loop = awaitable.loop
            elif isinstance(awaitable, Future) and callable(getattr(awaitable, "get_loop", None)):
                # asyncio's Future, in Python >= 3.7, gracefully exposes it's loop
                loop = awaitable.get_loop()
            elif isfuture(awaitable):
                loop = getattr(awaitable, "_loop", None)

        super().__init__(loop=loop, **kwargs)

        fut: "Future[K]" = (
            ensure_future(awaitable, loop=self.loop) if awaitable else self.loop.create_future()
        )

        fut.add_done_callback(self._schedule_callbacks)

        # Internal
        self._chain: Te.Deque[T.Tuple[T.Callable[[T.Any], T.Any], Promise[T.Any], ChainTypes]] = self.loop.create_future()
        self._awaited = False

        # Ensure that the chain also is cancelled if internal future is cancelled

    def __await__(self) -> T.Generator[T.Any, None, K]:
        """Python magic method called when awaiting an asynchronous object.

        Indirectly invoked by:
        >>> p = Promise()
        >>> await p # Internally python will call p.__await__

        Returns:
            A generator used internally by the async loop to manage the an awaitable life-cycle.
            A Promise redirects to it's internal future __await__().
        """
        self._awaited = True
        return self._fut.__await__()

    # make Promise compatible with 'yield from'.
    __iter__ = __await__

    def _schedule_callbacks(self, fut: "Future[K]"):
        assert fut is self._fut and fut.done

        if

    def _warn_on_unexpected_exception(self, fut: "Future[K]") -> None:
        assert fut is self._fut and fut.done()

        if self._awaited or fut.cancelled():
            return

        exc = fut.exception()
        if exc:
            assert self._exception_handler is None
            # Queue call_exception_handler execution to allow slightly delayed promise await to cancel it
            self._exception_handler = self.loop.call_soon(
                self.loop.call_exception_handler,
                {
                    "future": fut,
                    "message": "Unhandled exception propagated through non awaited Promise",
                    "exception": exc,
                },
            )

    def done(self) -> bool:
        """Check if promise is done.

        Returns:
            Boolean indicating if promise is done or not.

        """
        return self._fut.done()

    def cancel(self, *, chain: bool = True) -> bool:
        """Cancel the promise and chain.

        Returns:
            Boolean indicating if the cancellation occurred or not.

        """
        result = False
        if chain and self._chain:
            result = self._chain.cancel()

        return self._fut.cancel() or result

    def cancelled(self) -> bool:
        """Indicates whether promise is cancelled or not.

        Returns:
            Boolean indicating if promise is cancelled or not.

        """
        return self._fut.cancelled() or self._chain.cancelled()

    def resolve(self, result: K) -> None:
        """Resolve Promise with given value.

        Arguments:
            result: Result to resolve Promise with.

        Raises:
            InvalidStateError: Raised when promise was already resolved

        """
        if sys.version_info < (3, 7) and isinstance(self._fut, Task):
            # This is needs to exist because it's incorrectly allowed on Python <= 3.6
            raise RuntimeError("Task does not support set_result operation")

        self._fut.set_result(result)

    def reject(self, error: Exception) -> None:
        """Reject promise with given value.

        Arguments:
            error: Error to reject Promise with.

        Raises:
            InvalidStateError: Raised when promise was already resolved

        """
        if sys.version_info < (3, 7) and isinstance(self._fut, Task):
            # This is needs to exist because it's incorrectly allowed on Python < 3.7
            raise RuntimeError("Task does not support set_exception operation")

        self._fut.set_exception(error)

    @abstractmethod
    def then(self, on_fulfilled: T.Callable[[K], T.Any]) -> "Promise[T.Any]":
        """Chain a callback to be executed when the Promise resolves.

        Arguments:
            on_fulfilled: The callback, it must receive a single argument that
                is the result of the Promise.

        Raises:
            NotImplementedError

        Returns:
            Promise that will be resolved when the callback finishes executing.

        """
        raise NotImplementedError

    @abstractmethod
    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> "Promise[T.Any]":
        """Chain a callback to be executed when the Promise fails to resolve.

        Arguments:
            on_reject: The callback, it must receive a single argument that
                is the reason of the Promise resolution failure.

        Raises:
            NotImplementedError

        Returns:
            Promise that will be resolved when the callback finishes executing.

        """
        raise NotImplementedError

    @abstractmethod
    def lastly(self, on_fulfilled: T.Callable[[], T.Any]) -> "Promise[T.Any]":
        """Chain a callback to be executed when the Promise concludes.

        Arguments:
            on_fulfilled: The callback. No argument is passed to it.

        Raises:
            NotImplementedError

        Returns:
            Promise that will be resolved when the callback finishes executing.
        """
        raise NotImplementedError


__all__ = ("Promise",)
