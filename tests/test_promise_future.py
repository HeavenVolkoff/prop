# Internal
import unittest
from asyncio import Future, CancelledError, InvalidStateError

# External
import asynctest
from prop import Promise


# noinspection PyAttributeOutsideInit
@asynctest.strict
class TestPromiseFuture(asynctest.TestCase, unittest.TestCase):
    async def setUp(self):
        self.fut: Future = self.loop.create_future()

    def tearDown(self):
        self.fut.cancel()

    @asynctest.fail_on(unused_loop=False)
    def test_initialization(self):
        promise = Promise(self.fut)
        self.assertEqual(promise.loop, getattr(self.fut, "_loop"))
        self.assertEqual(promise.done(), self.fut.done())
        self.assertEqual(promise.cancelled(), self.fut.cancelled())

    @asynctest.fail_on(unused_loop=False)
    def test_invalid_state_promise(self):
        promise = Promise(self.fut)

        self.fut.set_result(None)
        with self.assertRaises(InvalidStateError):
            promise.resolve(None)

        with self.assertRaises(InvalidStateError):
            promise.reject(Exception())

        self.assertFalse(promise.cancel())

    @asynctest.fail_on(unused_loop=False)
    def test_invalid_state_future(self):
        promise = Promise(self.fut)

        promise.resolve(None)
        with self.assertRaises(InvalidStateError):
            self.fut.set_result(None)

        with self.assertRaises(InvalidStateError):
            self.fut.set_exception(Exception())

        self.assertFalse(self.fut.cancel())

    async def test_external_resolution(self):
        promise = Promise(self.fut)

        self.fut.set_result(None)
        result = await self.fut
        self.assertIsNone(result, None)
        self.assertEqual(result, await promise)

    async def test_resolution(self):
        promise = Promise(self.fut)

        promise.resolve(None)
        result = await promise
        self.assertIsNone(result)
        self.assertEqual(await self.fut, result)

    async def test_external_rejection(self):
        promise = Promise(self.fut, log_unexpected_exception=False)

        exc = Exception("test_external_rejection")
        self.fut.set_exception(exc)
        self.assertAsyncRaises(exc, promise)
        self.assertAsyncRaises(exc, self.fut)

    async def test_rejection(self):
        promise = Promise(self.fut, log_unexpected_exception=False)

        exc = Exception("test_rejection")
        promise.reject(exc)
        self.assertAsyncRaises(exc, promise)
        self.assertAsyncRaises(exc, self.fut)

    async def test_external_cancellation(self):
        promise = Promise(self.fut)

        self.fut.cancel()
        self.assertAsyncRaises(CancelledError, self.fut)
        self.assertAsyncRaises(CancelledError, promise)

    async def test_cancellation(self):
        promise = Promise(self.fut)

        promise.cancel()
        self.assertAsyncRaises(CancelledError, self.fut)
        self.assertAsyncRaises(CancelledError, promise)


if __name__ == "__main__":
    unittest.main()
