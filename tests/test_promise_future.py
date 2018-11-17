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
        self.promise = Promise(self.fut)

    def tearDown(self):
        self.fut.cancel()

    @asynctest.fail_on(unused_loop=False)
    def test_initialization(self):
        self.assertEqual(self.promise.loop, getattr(self.fut, "_loop"))
        self.assertEqual(self.promise.done(), self.fut.done())
        self.assertEqual(self.promise.cancelled(), self.fut.cancelled())

    @asynctest.fail_on(unused_loop=False)
    def test_invalid_state_promise(self):
        self.fut.set_result(None)
        with self.assertRaises(InvalidStateError):
            self.promise.resolve(None)

        with self.assertRaises(InvalidStateError):
            self.promise.reject(Exception())

        self.assertFalse(self.promise.cancel())

    @asynctest.fail_on(unused_loop=False)
    def test_invalid_state_future(self):
        self.promise.resolve(None)
        with self.assertRaises(InvalidStateError):
            self.fut.set_result(None)

        with self.assertRaises(InvalidStateError):
            self.fut.set_exception(Exception())

        self.assertFalse(self.fut.cancel())

    async def test_external_resolution(self):
        self.fut.set_result(None)
        result = await self.fut
        self.assertIsNone(result, None)
        self.assertEqual(result, await self.promise)

    async def test_resolution(self):
        self.promise.resolve(None)
        result = await self.promise
        self.assertIsNone(result)
        self.assertEqual(await self.fut, result)

    async def test_external_rejection(self):
        exc = Exception("Test")
        self.fut.set_exception(exc)
        self.assertAsyncRaises(exc, self.fut)
        self.assertAsyncRaises(exc, self.promise)

    async def test_rejection(self):
        exc = Exception("Test")
        self.promise.reject(exc)
        self.assertAsyncRaises(exc, self.fut)
        self.assertAsyncRaises(exc, self.promise)

    async def test_external_cancellation(self):
        self.fut.cancel()
        self.assertAsyncRaises(CancelledError, self.fut)
        self.assertAsyncRaises(CancelledError, self.promise)

    async def test_cancellation(self):
        self.promise.cancel()
        self.assertAsyncRaises(CancelledError, self.fut)
        self.assertAsyncRaises(CancelledError, self.promise)


if __name__ == "__main__":
    unittest.main()
