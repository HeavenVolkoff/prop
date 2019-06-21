# Internal
import unittest
from asyncio import Future, CancelledError, sleep as asleep

# External
import asynctest
from prop import Promise

DEFAULT_SLEEP = 0.05


async def sum_with_sleep(x, y):
    await asleep(DEFAULT_SLEEP)
    return x + y


# noinspection PyAttributeOutsideInit
@asynctest.strict
class TestPromiseChain(asynctest.TestCase, unittest.TestCase):
    async def setUp(self):
        self.fut = self.loop.create_future()
        self.exc_ctx = None
        self.exc_ctx_count = 0

        def exc_handler(_, ctx):
            self.exc_ctx = ctx
            self.exc_ctx_count += 1

        self.loop.set_exception_handler(exc_handler)

    def tearDown(self):
        self.fut.cancel()
        self.loop.set_exception_handler(None)

    async def test_resolve(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            result = await p.then(lambda x: x * 2).then(lambda x: x + 2).then(lambda x: x / 2)

        self.assertEqual(result, 11)

    async def test_reject(self):
        temp = {}
        with Promise(self.fut) as p:
            p.reject(Exception())
            result = (
                await p.then(lambda x: temp.setdefault("then", 1))
                .catch(lambda exc: temp.setdefault("catch", 1))
                .then(lambda x: x + 10)
                .then(lambda x: x * 2)
            )

        self.assertNotIn("then", temp)
        self.assertIn("catch", temp)
        self.assertEqual(temp["catch"], 1)

        self.assertEqual(result, 22)

    async def test_resolve_lastly(self):
        temp = {}
        with Promise(self.fut) as p:
            p.resolve(10)
            result = await p.then(lambda x: x * 2).lastly(lambda: temp.setdefault("lastly", 100))

        self.assertEqual(result, 20)
        self.assertIn("lastly", temp)
        self.assertEqual(temp["lastly"], 100)

    async def test_unhandled_exception(self):
        async def raise_exc():
            raise RuntimeError

        task = self.loop.create_task(raise_exc())

        p = Promise(task)

        with self.assertRaises(RuntimeError):
            await task

        # Wait till next loop cycle
        await asleep(0)

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
        await asleep(0)

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
        await asleep(0)

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
        await asleep(0)

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
        await asleep(0)

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
        await asleep(0.1)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)

    async def test_ignore_unhandled_cancellation_error(self):
        fut = self.loop.create_future()

        p = Promise(fut)

        fut.cancel()
        with self.assertRaises(CancelledError):
            await fut

        # Wait till next loop cycle
        await asleep(0)

        self.assertEqual(self.exc_ctx_count, 0)
        self.assertIsNone(self.exc_ctx)
        with self.assertRaises(CancelledError):
            await p

    async def test_resolve_promises_inception(self):
        start_time = self.loop.time()
        with Promise(self.fut, loop=self.loop) as p:
            p.resolve(10)
            result = (
                await p.then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
                .then(lambda x: Promise(sum_with_sleep(x, 10), loop=self.loop))
            )

        end_time = self.loop.time()

        self.assertAlmostEqual(DEFAULT_SLEEP * 9, end_time - start_time, places=1)
        self.assertEqual(result, 100)

    async def test_cancellation_managed_1(self):
        with Promise(self.fut) as p:
            t = p.then(lambda x: x * 2)
            t.cancel()

            with self.assertRaises(CancelledError):
                await t

        self.assertTrue(t.done())
        self.assertTrue(t.cancelled())

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())

    async def test_cancellation_managed_2(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t = p.then(lambda x: x * 2)
            t.cancel()

            with self.assertRaises(CancelledError):
                await t

            self.assertEqual(await p, 10)

        self.assertTrue(t.done())
        self.assertTrue(t.cancelled())

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())

    async def test_cancellation_lastly(self):
        temp = {}
        with Promise(self.fut) as p:
            p.cancel()

            with self.assertRaises(CancelledError):
                await p.then(lambda x: temp.setdefault("then", x)).lastly(
                    lambda: temp.setdefault("lastly", 100)
                )

        self.assertNotIn("then", temp)
        self.assertNotIn("lastly", temp)

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())

    async def test_cancel_lastly(self):
        temp = {}
        with Promise(self.fut) as p:
            p.resolve(10)
            t = p.then(lambda x: x * 2)
            l = t.lastly(lambda: temp.setdefault("lastly", 100))
            l.cancel()

            with self.assertRaises(CancelledError):
                await l

            self.assertEqual(await t, 20)

        self.assertNotIn("lastly", temp)

    async def test_cancellation_reject(self):
        temp = {}
        with Promise(self.fut) as p:
            p.cancel()

            with self.assertRaises(CancelledError):
                (
                    await p.then(lambda x: temp.setdefault("then", 1))
                    .catch(lambda exc: temp.setdefault("catch", 1))
                    .lastly(lambda: temp.setdefault("lastly", 1))
                )

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())
        self.assertNotIn("then", temp)
        self.assertNotIn("catch", temp)
        self.assertNotIn("lastly", temp)

    async def test_chain_no_external_resolve(self):
        with Promise(self.fut) as p:
            self.assertTrue(callable(getattr(p, "resolve")))
            self.assertTrue(callable(getattr(p, "reject")))

            t = p.then(lambda x: x * 2)

            self.assertFalse(hasattr(t, "resolve"))
            self.assertFalse(hasattr(t, "reject"))

            p.resolve(10)
            result = await t

        self.assertEqual(result, 20)

    async def test_chain_cancellation_sync(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(lambda x: x * 2)
            t2 = t1.then(lambda x: x * 2)
            t3 = t2.then(lambda x: x * 2)

            self.assertEqual(await p, 10)

        with self.assertRaises(CancelledError):
            await p._notify_chain

        self.assertEqual(await t1, 20)
        self.assertEqual(await t2, 40)
        self.assertEqual(await t3, 80)

    async def test_chain_cancellation_async(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(lambda x: sum_with_sleep(x, 10))
            t2 = t1.then(lambda x: x * 2)
            t3 = t2.then(lambda x: sum_with_sleep(x, 10))

            self.assertEqual(await p, 10)

        with self.assertRaises(CancelledError):
            await t1

        with self.assertRaises(CancelledError):
            await t2

        with self.assertRaises(CancelledError):
            await t3

    async def test_chain_cancellation_branch(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(lambda x: sum_with_sleep(x, 10))
            t2 = p.then(lambda x: x * 2)
            t3 = p.then(lambda x: sum_with_sleep(x, 10))

            t1.cancel()

            self.assertEqual(await p, 10)

            with self.assertRaises(CancelledError):
                await t1

            self.assertEqual(await t2, 20)
            self.assertEqual(await t3, 20)

    async def test_chain_after_cancellation_after_resolution(self):
        with Promise(self.fut) as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

        t2 = t1.then(lambda x: sum_with_sleep(x, 10))

        with self.assertRaises(CancelledError):
            await t2

    async def test_chain_cancellation_after_resolution_2(self):
        with Promise(self.fut) as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

            t2 = t1.then(lambda x: sum_with_sleep(x, 10))

            t1.cancel()

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_after_resolution_3(self):
        with Promise(self.fut) as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

            t2 = t1.then(lambda x: sum_with_sleep(x, 10))

            p.cancel()

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_sync_edge_case(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(lambda x: x * 2)
            self.assertEqual(await p, 10)

        with self.assertRaises(CancelledError):
            await p._notify_chain

        self.assertEqual(await t1, 20)

        t2 = t1.then(lambda x: sum_with_sleep(x, 10))

        with self.assertRaises(CancelledError):
            await t2

    async def test_task_cancellation(self):
        a = {}

        async def task(_):
            t1.cancel()
            a["test"] = 10
            await asleep(DEFAULT_SLEEP)
            a["shouldnt_exist"] = 10

        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(task)
            self.assertNotIn("test", a)
            self.assertNotIn("shouldnt_exist", a)
            with self.assertRaises(CancelledError):
                await t1
            self.assertIn("test", a)
            self.assertNotIn("shouldnt_exist", a)

    async def test_promise_of_a_promise(self):
        p = Promise()
        p2 = Promise(p)

        p.resolve(0)

        self.assertEqual(await p2.then(lambda x: 1 / x).catch(lambda exc: 0), 0)

    async def test_promise_cancelled(self):
        b = False

        async def a():
            nonlocal b
            b = True

        p = Promise()
        lp = p.lastly(a)

        p.cancel()

        with self.assertRaises(CancelledError):
            await p
        with self.assertRaises(CancelledError):
            await lp

        self.assertFalse(b)

    async def test_promise_cancelled_2(self):
        b = False

        async def a():
            nonlocal b
            b = True

        p = Promise()
        lp = p.lastly(a)

        p.resolve(10)
        lp.cancel()

        with self.assertRaises(CancelledError):
            await lp

        self.assertEqual(await p, 10)
        self.assertFalse(b)


if __name__ == "__main__":
    unittest.main()
