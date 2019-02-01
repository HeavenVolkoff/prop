# Internal
import typing as T
from abc import ABCMeta, abstractmethod
from asyncio import Task, Future, AbstractEventLoop, InvalidStateError, isfuture, ensure_future

# External
from async_tools import Loopable
from async_tools.abstract import Loopable as AbstractLoopable, BasicRepr

# Generic types
K = T.TypeVar("K")


class Promise(BasicRepr, Loopable, T.Awaitable[K], metaclass=ABCMeta):
    """An abstract Promise implementation that encapsulate an awaitable.

    .. Warning::

        This class is abstract in the sense that no implementation is made as to
        how the callback chain is generated or maintained.
    """

    __slots__ = ("_fut",)

    def __init__(
        self,
        awaitable: T.Optional[T.Union[T.Awaitable[K], T.Coroutine[T.Any, T.Any, K]]] = None,
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
        # Retrieve loop from awaitable if available
        if loop is None:
            if isinstance(awaitable, AbstractLoopable):
                loop = awaitable.loop
            elif isfuture(awaitable):
                try:
                    get_loop = awaitable.get_loop  # type: ignore
                except AttributeError:  # Python <= 3.7
                    loop = getattr(awaitable, "_loop", None)
                else:
                    loop = get_loop()

        super().__init__(loop=loop, **kwargs)

        # Internal
        self._fut: Future[K] = (
            ensure_future(awaitable, loop=self.loop) if awaitable else self.loop.create_future()
        )
        self._notify_chain: T.Optional["Future[None]"] = None

        # Warning if exception is raised inside Promise but it is not waited
        if log_unexpected_exception:
            self._fut.add_done_callback(self._warn_on_unexpected_exception)

    def __await__(self) -> T.Generator[T.Any, None, K]:
        self._fut.remove_done_callback(self._warn_on_unexpected_exception)
        return self._fut.__await__()

    def _warn_on_unexpected_exception(self, fut: Future):
        if not fut.done() or fut.cancelled():
            return

        exc = fut.exception()

        if exc:
            self.loop.call_exception_handler(
                {
                    "message": "Unhandled exception propagated through non awaited Promise",
                    "future": fut,
                    "exception": exc,
                }
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
        if isinstance(self._fut, Task):
            raise InvalidStateError(
                "Promises that are derived from Tasks or part"
                "of a chain can't be resolved externally"
            )

        self._fut.set_result(result)

    def reject(self, error: Exception) -> None:
        """Reject promise with given value.

        Arguments:
            error: Error to reject Promise with.

        Raises:
            InvalidStateError: Raised when promise was already resolved

        """
        if isinstance(self._fut, Task):
            raise InvalidStateError(
                "Promises that are derived from Tasks or part"
                "of a chain can't be rejected externally"
            )

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
