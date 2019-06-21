# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Internal
import typing as T
from asyncio import Future, AbstractEventLoop, isfuture, ensure_future
from inspect import currentframe
from weakref import ReferenceType
from functools import partial
from traceback import FrameSummary, format_list, extract_stack

# External
from async_tools import Loopable
from async_tools.abstract import Loopable as AbstractLoopable

# Project
from ._helper import reject, fulfill, resolve

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class ChainLink(T.Awaitable[K], Loopable):
    @staticmethod
    def log_unhandled_exception(stack: FrameSummary, fut: "Future[T.Any]") -> None:
        assert fut.done()

        get_loop: T.Callable[[], AbstractEventLoop] = getattr(fut, "get_loop", None)
        loop: AbstractEventLoop = get_loop() if callable(get_loop) else getattr(fut, "_loop", None)

        assert loop is not None

        if fut.cancelled():
            return

        exc = fut.exception()
        if exc is not None:
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
        # TODO: Add a test case for stack propagation
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
        # TODO: Add a test case for stack propagation
        self._stack = (
            extract_stack(f=currentframe(), limit=2)[:1]
            if stack is None
            else (stack + extract_stack(f=currentframe(), limit=3)[:1])
        )
        self._notify_chain: "Future[None]" = self.loop.create_future()

        # Schedule exception handler
        if log_unhandled_exception:
            exc_handler = partial(self.log_unhandled_exception, self._stack)
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
            # TODO: Add test cases to ensure that the log is correctly being disabled
            self._clear_exc_handler()
            self._clear_exc_handler = None
        return self._fut.__await__()

    # make Promise compatible with 'yield from'.
    __iter__ = __await__

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
        next_link = ChainLink(resolve(self, resolution_cb), loop=self.loop, stack=self._stack)
        self._notify_chain.add_done_callback(lambda _: next_link.cancel())
        return next_link

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
        next_link = ChainLink(reject(self, rejection_cb), loop=self.loop, stack=self._stack)
        self._notify_chain.add_done_callback(lambda _: next_link.cancel())
        return next_link

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
        next_link = ChainLink(fulfill(self, fulfillment_cb), loop=self.loop, stack=self._stack)
        self._notify_chain.add_done_callback(lambda _: next_link.cancel())
        return next_link


__all__ = ("ChainLink",)
