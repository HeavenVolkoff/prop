# Internal
import typing as T
from asyncio import CancelledError

# External
from async_tools import attempt_await

# Generic types
K = T.TypeVar("K")
L = T.TypeVar("L")


@T.overload
async def resolve(awaitable: T.Awaitable[K], cb: T.Callable[[K], T.Awaitable[L]]) -> L:
    ...


@T.overload
async def resolve(awaitable: T.Awaitable[K], cb: T.Callable[[K], L]) -> L:
    ...


async def resolve(awaitable: T.Awaitable[K], cb: T.Callable[[K], T.Any]) -> T.Any:
    return await attempt_await(cb(await awaitable))


@T.overload
async def reject(
    awaitable: T.Awaitable[K], cb: T.Callable[[Exception], T.Awaitable[L]]
) -> T.Union[K, L]:
    ...


@T.overload
async def reject(awaitable: T.Awaitable[K], cb: T.Callable[[Exception], L]) -> T.Union[K, L]:
    ...


async def reject(awaitable: T.Awaitable[K], cb: T.Callable[[Exception], T.Any]) -> T.Any:
    try:
        return await awaitable
    except CancelledError:
        raise
    except Exception as exc:
        return await attempt_await(cb(exc))


async def fulfill(awaitable: T.Awaitable[K], cb: T.Callable[[], T.Any]) -> K:
    cancelled = False
    try:
        return await awaitable
    except CancelledError:
        cancelled = True
        raise
    except Exception:
        raise
    except BaseException:
        cancelled = True
        raise
    finally:
        if not cancelled:
            await attempt_await(cb())
