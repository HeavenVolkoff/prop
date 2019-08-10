# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Internal
import typing as T
from asyncio import Future, CancelledError, AbstractEventLoop, isfuture, ensure_future
from inspect import currentframe
from weakref import proxy
from functools import partial
from traceback import FrameSummary, StackSummary, format_list, extract_stack
from contextlib import suppress

# External
from async_tools import Loopable
from async_tools.abstract import Loopable as AbstractLoopable

# Project
from ._helper import reject, fulfill, resolve

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")

# Fake stacktrace information for use when no stack can be recovered from promise
_FAKE_STACK = list(StackSummary.from_list([("unknown", 0, "unknown", "invalid")]))


class ChainLink(T.Awaitable[K], Loopable):
    @staticmethod
    def log_unhandled_exception(promise: "ChainLink[T.Any]", fut: "Future[T.Any]") -> None:
        assert fut.done()

        get_loop: T.Callable[[], AbstractEventLoop] = getattr(fut, "get_loop", None)
        loop: AbstractEventLoop = get_loop() if callable(get_loop) else getattr(fut, "_loop", None)

        assert loop is not None

        # noinspection PyUnusedLocal
        stack = _FAKE_STACK
        # noinspection PyUnusedLocal
        suppress_log = True
        with suppress(ReferenceError):
            stack = promise._stack
            suppress_log = promise._clear_exc_handler is None

        exc = None if fut.cancelled() else fut.exception()
        if isinstance(exc, CancelledError) or suppress_log or exc is None:
            return

        loop.call_exception_handler(
            {
                "future": fut,
                "message": (
                    "Unhandled exception propagated through promise:\n"
                    + "".join(format_list(stack))[:-1]
                ),
                "exception": exc,
            }
        )

    def __init__(
        self,
        awaitable: T.Optional[T.Awaitable[K]] = None,
        *,
        loop: T.Optional[AbstractEventLoop] = None,
        log_unhandled_exception: bool = True,
        **kwargs: T.Any,
    ) -> None:
        """ChainLink constructor.

        Arguments:
            awaitable: The awaitable object to be encapsulated.
            loop: Current asyncio loop.
            log_unhandled_exception: Flag indicating whether we should log unhandled exception
                raised inside the promise chain.
            kwargs: Keyword parameters for super.

        """
        stack = kwargs.pop("stack", None)

        if loop is None:
            # Retrieve loop from awaitable if available
            if isinstance(awaitable, AbstractLoopable):
                loop = awaitable.loop
            elif isinstance(awaitable, Future) and callable(getattr(awaitable, "get_loop", None)):
                # asyncio's Future, in Python >= 3.7
                loop = awaitable.get_loop()
            elif isfuture(awaitable):
                # asyncio's Future, in Python < 3.7
                loop = getattr(awaitable, "_loop", None)

        super().__init__(loop=loop, **kwargs)

        # --- Internal ---
        self._fut: "Future[K]" = (
            self.loop.create_future()
            if awaitable is None
            else ensure_future(awaitable, loop=self.loop)
        )
        self._stack: T.List[FrameSummary] = (
            extract_stack(f=currentframe(), limit=2)[:1]
            if stack is None
            else (stack + extract_stack(f=currentframe(), limit=4)[:1])
        )
        self._notify_chain: "Future[None]" = self.loop.create_future()

        # Schedule exception handler
        if log_unhandled_exception:
            exc_handler = partial(self.log_unhandled_exception, proxy(self))
            self._fut.add_done_callback(exc_handler)
            self._clear_exc_handler: T.Optional[T.Callable[[], T.Any]] = partial(
                self._fut.remove_done_callback, exc_handler
            )
        else:
            self._clear_exc_handler = None

    def __await__(self) -> T.Generator[T.Any, None, K]:
        """Python magic method called when awaiting an asynchronous object.

        Indirectly invoked by:
        >>> c = ChainLink()
        >>> await c # Internally python will call p.__await__

        Returns:
            A generator used internally by the async loop to manage the an awaitable life-cycle.
            A Promise redirects to it's internal future __await__().
        """
        if self._clear_exc_handler is not None:
            self._clear_exc_handler()
            self._clear_exc_handler = None

        return self._fut.__await__()

    # make Promise compatible with 'yield from'.
    __iter__ = __await__

    def _chain(self, coro: T.Coroutine[T.Any, T.Any, L]) -> "ChainLink[L]":
        next_link = ChainLink(coro, loop=self.loop, stack=self._stack)
        self._notify_chain.add_done_callback(lambda _: next_link.cancel())
        if self._clear_exc_handler is not None:
            self._clear_exc_handler()
            self._clear_exc_handler = None

        return next_link

    def done(self) -> bool:
        """Check if chain link is done.

        Returns:
            Boolean indicating if chain link is done or not.

        """
        return self._fut.done()

    def cancel(self) -> bool:
        """Cancel chain.

        Returns:
            Boolean indicating if the cancellation occurred or not.

        """
        self._fut.cancel()
        self._notify_chain.cancel()

        return True

    def cancelled(self) -> bool:
        """Indicates whether promise is cancelled or not.

        Returns:
            Boolean indicating if promise is cancelled or not.

        """
        return self._fut.cancelled() or self._notify_chain.cancelled()

    @T.overload
    def then(self, resolution_cb: T.Callable[[K], T.Awaitable[L]]) -> "ChainLink[L]":
        ...

    @T.overload
    def then(self, resolution_cb: T.Callable[[K], L]) -> "ChainLink[L]":
        ...

    def then(self, resolution_cb: T.Callable[[K], T.Any]) -> "ChainLink[T.Any]":
        """Chain a callback to be executed on resolution.

        Arguments:
            resolution_cb: Callback that will receive the result of the resolution.

        Returns:
            New ChainLink that will be resolved when the callback finishes executing.

        """
        return self._chain(resolve(self, resolution_cb))

    @T.overload
    def catch(self, rejection_cb: T.Callable[[Exception], T.Awaitable[L]]) -> "ChainLink[L]":
        ...

    @T.overload
    def catch(self, rejection_cb: T.Callable[[Exception], L]) -> "ChainLink[L]":
        ...

    def catch(self, rejection_cb: T.Callable[[Exception], T.Any]) -> "ChainLink[T.Any]":
        """Chain a callback to be executed on rejection/failure.

        Arguments:
            rejection_cb: Callback that will receive the exception that cause the rejection.

        Returns:
            New ChainLink that will be resolved when the callback finishes executing.

        """
        return self._chain(reject(self, rejection_cb))

    @T.overload
    def lastly(self, fulfillment_cb: T.Callable[[], T.Awaitable[L]]) -> "ChainLink[L]":
        ...

    @T.overload
    def lastly(self, fulfillment_cb: T.Callable[[], L]) -> "ChainLink[L]":
        ...

    def lastly(self, fulfillment_cb: T.Callable[[], T.Any]) -> "ChainLink[T.Any]":
        """Chain a callback to be executed on fulfillment.

        Arguments:
            fulfillment_cb: Callback for fulfilment.

        Returns:
            New ChainLink that will be resolved when the callback finishes executing.

        """
        return self._chain(fulfill(self, fulfillment_cb))


__all__ = ("ChainLink",)
