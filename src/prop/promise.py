# Internal
import typing as T

# Project
from .chain_promise import ChainPromise, ChainLinkPromise

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


class Promise(ChainPromise[K], T.ContextManager["Promise[K]"]):
    def __init__(
        self,
        awaitable: T.Optional[T.Awaitable[K]] = None,
        *,
        warn_no_management: bool = True,
        **kwargs: T.Any,
    ) -> None:
        super().__init__(awaitable, **kwargs)

        self._is_managed = not warn_no_management

    def __enter__(self) -> "Promise[K]":
        self._is_managed = True
        return self

    def __exit__(self, _: T.Any, __: T.Any, ___: T.Any) -> T.Optional[bool]:
        self.cancel(chain=True)
        return False

    def _assert_management(self) -> None:
        if self._is_managed:
            return

        self.loop.call_exception_handler(
            {"message": f"{self} is being chained without proper life-cycle management."}
        )

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], T.Awaitable[L]]) -> ChainLinkPromise[L, K]:
        ...  # pragma: no cover

    @T.overload
    def then(self, on_fulfilled: T.Callable[[K], L]) -> ChainLinkPromise[L, K]:
        ...  # pragma: no cover

    def then(self, on_fulfilled: T.Callable[[K], T.Any]) -> ChainLinkPromise[T.Any, T.Any]:
        """Add management control to then

        See: :meth:`~.promise.Promise.then` for more information.

        """
        self._assert_management()
        return super().then(on_fulfilled)

    @T.overload
    def catch(
        self, on_reject: T.Callable[[Exception], T.Awaitable[L]]
    ) -> ChainLinkPromise[T.Union[L, K], K]:
        ...  # pragma: no cover

    @T.overload
    def catch(self, on_reject: T.Callable[[Exception], L]) -> ChainLinkPromise[T.Union[L, K], K]:
        ...  # pragma: no cover

    def catch(self, on_reject: T.Callable[[Exception], T.Any]) -> ChainLinkPromise[T.Any, T.Any]:
        """Add management control to catch

        See: :meth:`~.promise.Promise.catch` for more information.

        """
        self._assert_management()
        return super().catch(on_reject)

    def lastly(self, on_resolved: T.Callable[[], T.Any]) -> ChainLinkPromise[K, K]:
        """Add management control to lastly

        See: :meth:`~.promise.Promise.lastly` for more information.

        """
        self._assert_management()
        return super().lastly(on_resolved)


__all__ = ("Promise",)
