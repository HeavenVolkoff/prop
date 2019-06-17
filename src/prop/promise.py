from warnings import warn
import typing as T

# Project
from .abstract import Promise as AbstractPromise
from .chain_link import FulfillmentPromise, RejectionPromise, ResolutionPromise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class Promise(AbstractPromise[K], T.ContextManager["Promise[K]"]):
    def __init__(self, awaitable: T.Optional[T.Awaitable[K]] = None, **kwargs: T.Any) -> None:
        super().__init__(awaitable, **kwargs)

        # Internal
        self._managed = True

    def __enter__(self) -> "Promise[K]":
        self._managed = True
        return self

    def __exit__(self, _: T.Any, __: T.Any, ___: T.Any) -> T.Optional[bool]:
        self.cancel()
        return False

    def _assert_management(self) -> None:
        if not self._managed:
            warn(f"{self} is being chained without proper life-cycle management.", RuntimeWarning)

    def self_managed(self) -> "Promise[K]":
        self._managed = True
        return self

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], T.Awaitable[L]]) -> "ChainLinkPromise[L, K]":
        ...

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], L]) -> "ChainLinkPromise[L, K]":
        ...

    def then(self, on_fulfilled: T.Callable[[K], T.Any]) -> "ChainLinkPromise[T.Any, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if no exception is raised, it will call the callback with the promise
        result.

        See: :meth:`~.abstract.promise.Promise.then` for more information.

        """
        return FulfillmentPromise(self, on_fulfilled, loop=self._loop)

    @T.overload
    def catch(
        self, on_reject: T.Callable[[Exception], T.Awaitable[L]]
    ) -> "ChainLinkPromise[T.Union[L, K], K]":
        ...

    @T.overload
    def catch(self, on_reject: T.Callable[[Exception], L]) -> "ChainLinkPromise[T.Union[L, K], K]":
        ...

    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> "ChainLinkPromise[T.Any, T.Any]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and,
        if a exception is raised, it will call the callback with the promise
        exception.

        See: :meth:`~.abstract.promise.Promise.catch` for more information.

        """
        return RejectionPromise(self, on_reject, loop=self._loop)

    def lastly(self, on_resolved: T.Callable[[], T.Any]) -> "ChainLinkPromise[K, K]":
        """Concrete implementation that wraps the received callback on a :class:`~typing.Coroutine`.
        The :class:`~typing.Coroutine` will await the promise resolution and
        call the callback.

        See: :meth:`~.abstract.promise.Promise.lastly` for more information.

        """
        return ResolutionPromise(self, on_resolved, loop=self._loop)


__all__ = ("Promise",)
