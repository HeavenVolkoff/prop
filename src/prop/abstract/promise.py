# Internal
import sys
import typing as T
from abc import ABCMeta, abstractmethod
from asyncio import Task, Future, Handle, AbstractEventLoop, isfuture, ensure_future

# External
from async_tools import Loopable
from async_tools.abstract import Loopable as AbstractLoopable, BasicRepr

# Generic types
K = T.TypeVar("K")

_AWAITED = object()  # sentinel object to detect when a Promise was awaited


class Promise(BasicRepr, Loopable, T.Awaitable[K], metaclass=ABCMeta):
    """An abstract Promise implementation that encapsulate an awaitable.

    .. Warning::

        This class is abstract in the sense that no implementation is made as to
        how the callback chain is generated or maintained.
    """

    __slots__ = ("_fut",)

    @T.overload
    def __init__(
        self,
        awaitable: None,
        *,
        loop: T.Optional[AbstractEventLoop] = None,
        log_unexpected_exception: bool = True,
        **kwargs: T.Any,
    ) -> None:
        ...  # pragma: no cover

    @T.overload
    def __init__(
        self,
        awaitable: T.Awaitable[K],
        *,
        loop: T.Optional[AbstractEventLoop] = None,
        log_unexpected_exception: bool = True,
        **kwargs: T.Any,
    ) -> None:
        ...  # pragma: no cover

    @T.overload
    def __init__(
        self, awaitable: "Future[K]", *, log_unexpected_exception: bool = True, **kwargs: T.Any
    ) -> None:
        ...  # pragma: no cover

    def __init__(
        self,
        awaitable: T.Any = None,
        *,
        loop: T.Optional[AbstractEventLoop] = None,
        log_unexpected_exception: bool = True,
        **kwargs: T.Any,
    ) -> None:
        """Promise constructor.

        Arguments:
            awaitable: The awaitable object to be encapsulated.
            loop: Current asyncio loop.
            kwargs: Keyword parameters for super.

        """
        if loop is None:
            # Retrieve loop from awaitable if available
            if isinstance(awaitable, AbstractLoopable):
                loop = awaitable.loop
            elif isfuture(awaitable):
                loop = (
                    awaitable.get_loop()
                    if hasattr(awaitable, "get_loop")
                    else getattr(awaitable, "_loop", None)  # Python < 3.7
                )

        super().__init__(loop=loop, **kwargs)

        # Internal
        self._fut: Future[K] = (
            ensure_future(awaitable, loop=self.loop) if awaitable else self.loop.create_future()
        )
        self._notify_chain: T.Optional["Future[None]"] = None
        self._unexpected_exception_warning: T.Optional[object] = None

        if log_unexpected_exception:
            # Warn if exception is raised inside a not awaited Promise
            self._fut.add_done_callback(self._warn_on_unexpected_exception)
        else:
            # Promise was explicitly set to no warn on error, se we assume it's already awaited
            self._unexpected_exception_warning = _AWAITED

    def __await__(self) -> T.Generator[T.Any, None, K]:
        if self._unexpected_exception_warning is not _AWAITED:
            # First time awaiting this promise, cancel warning
            if isinstance(self._unexpected_exception_warning, Handle):
                # Internal future was already resolved, cancel warning directly
                self._unexpected_exception_warning.cancel()
            else:
                # Internal future is still pending, remove warning callback
                self._fut.remove_done_callback(self._warn_on_unexpected_exception)

            # Set this promised as awaited
            self._unexpected_exception_warning = _AWAITED

        return self._fut.__await__()

    __iter__ = __await__  # make compatible with 'yield from'.

    def _warn_on_unexpected_exception(self, fut: "Future[K]") -> None:
        assert fut is self._fut and fut.done()

        if self._unexpected_exception_warning is _AWAITED or fut.cancelled():
            return

        exc = fut.exception()

        if exc:
            assert self._unexpected_exception_warning is None
            self._unexpected_exception_warning = self.loop.call_soon(
                self.loop.call_exception_handler,
                {
                    "future": fut,
                    "message": "Unhandled exception propagated through non awaited Promise",
                    "exception": exc,
                },
            )

    @property
    def notify_chain(self) -> "Future[None]":
        if self._notify_chain is None:
            self._notify_chain = self.loop.create_future()

        return self._notify_chain

    def done(self) -> bool:
        """Check if promise is done.

        Returns:
            Boolean indicating if promise is done or not.

        """
        return self._fut.done()

    def cancel(self, *, chain: bool = False) -> bool:
        """Cancel the promise and chain.

        Returns:
            Boolean indicating if the cancellation occurred or not.

        """
        if self._fut.cancel():
            return True

        if chain and self._notify_chain:
            self._notify_chain.cancel()
            return True

        return False

    def cancelled(self) -> bool:
        """Indicates whether promise is cancelled or not.

        Returns:
            Boolean indicating if promise is cancelled or not.

        """
        return self._fut.cancelled()

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
            NotImplemented

        Returns:
            Promise that will be resolved when the callback finishes executing.

        """
        raise NotImplemented()

    @abstractmethod
    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> "Promise[T.Any]":
        """Chain a callback to be executed when the Promise fails to resolve.

        Arguments:
            on_reject: The callback, it must receive a single argument that
                is the reason of the Promise resolution failure.

        Raises:
            NotImplemented

        Returns:
            Promise that will be resolved when the callback finishes executing.

        """
        raise NotImplemented()

    @abstractmethod
    def lastly(self, on_fulfilled: T.Callable[[], T.Any]) -> "Promise[T.Any]":
        """Chain a callback to be executed when the Promise concludes.

        Arguments:
            on_fulfilled: The callback. No argument is passed to it.

        Raises:
            NotImplemented

        Returns:
            Promise that will be resolved when the callback finishes executing.
        """
        raise NotImplemented()


__all__ = ("Promise",)
