# Internal
import unittest
from asyncio import CancelledError, sleep

# External
import asynctest
from prop import Promise


@asynctest.strict
class TestPromiseChain(asynctest.TestCase, unittest.TestCase):
    async def setUp(self):
        self.exc_ctx = None
        self.exc_ctx_count = 0

        def exc_handler(_, ctx):
            self.exc_ctx = ctx
            self.exc_ctx_count += 1

        self.loop.set_exception_handler(exc_handler)

    def tearDown(self):
        self.loop.set_exception_handler(None)

    async def test_unhandled_exception(self):
        async def raise_exc():
            raise RuntimeError

        task = self.loop.create_task(raise_exc())

        p = Promise(task)

        with self.assertRaises(RuntimeError):
            await task

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(self.exc_ctx_count, 1)
        self.assertIsNotNone(self.exc_ctx)
        self.assertIn("message", self.exc_ctx)
        self.assertIsInstance(self.exc_ctx["exception"], RuntimeError)

        with self.assertRaises(RuntimeError):
            await p

    async def test_unhandled_exception_2(self):
        async def raise_exc(_):
            raise RuntimeError

        p = Promise(raise_exc(None)).catch(raise_exc)

        with self.assertRaises(RuntimeError):
            await p._fut  # bypass promise __await__

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(self.exc_ctx_count, 1)
        self.assertIsNotNone(self.exc_ctx)
        self.assertIn("message", self.exc_ctx)
        self.assertIsInstance(self.exc_ctx["exception"], RuntimeError)

        with self.assertRaises(RuntimeError):
            await p

    async def test_unhandled_exception_3(self):
        async def raise_exc():
            raise RuntimeError

        b = {}
        p = Promise(raise_exc()).then(lambda _: 10).lastly(lambda: b.setdefault("lastly", None))

        with self.assertRaises(RuntimeError):
            await p._fut  # bypass promise __await__

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(await p.catch(lambda exc: "success"), "success")
        self.assertEqual(self.exc_ctx_count, 1)
        self.assertIsNotNone(self.exc_ctx)
        self.assertIn("message", self.exc_ctx)
        self.assertIsInstance(self.exc_ctx["exception"], RuntimeError)
        self.assertIn("lastly", b)

    async def test_ignore_unhandled_exception(self):
        async def raise_exc():
            raise RuntimeError

        task = self.loop.create_task(raise_exc())

        p = Promise(task, log_unhandled_exception=False)

        with self.assertRaises(RuntimeError):
            await task

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)
        with self.assertRaises(RuntimeError):
            await p

    async def test_ignore_unhandled_exception_2(self):
        async def raise_exc():
            raise RuntimeError

        p = Promise(raise_exc()).catch(lambda exc: "success")

        await p._fut  # bypass promise __await__

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)
        self.assertEqual(await p, "success")

    async def test_ignore_unhandled_exception_3(self):
        async def raise_exc():
            raise RuntimeError

        p = Promise(raise_exc())

        with self.assertRaises(RuntimeError):
            await p

        # Wait till next loop cycle
        await sleep(0.1)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)

    async def test_ignore_unhandled_cancellation_error(self):
        fut = self.loop.create_future()

        p = Promise(fut)

        fut.cancel()
        with self.assertRaises(CancelledError):
            await fut

        # Wait till next loop cycle
        await sleep(0)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)
        with self.assertRaises(CancelledError):
            await p

    async def test_future_log_traceback(self):
        import gc

        fut = self.loop.create_future()
        fut.set_exception(RuntimeError)

        p = Promise(fut)
        del fut, p

        gc.collect()
        await sleep(0)

    async def test_task_log_destroy_pending(self):
        pass
