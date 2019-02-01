# Internal
import unittest
from asyncio import Future, CancelledError, InvalidStateError, sleep as asleep

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
        self.fut: Future = self.loop.create_future()
        self.exception_ctx = None

        self.loop.set_exception_handler(lambda l, c: setattr(self, "exception_ctx", c))

    def tearDown(self):
        self.fut.cancel()

    async def test_resolve(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            result = await p.then(lambda x: x * 2).then(lambda x: x + 2).then(lambda x: x / 2)

        self.assertEqual(result, 11)

    async def test_resolve_no_management(self):
        self.fut.set_result(10)
        result = (
            await Promise(self.fut)
            .then(lambda x: x * 2)
            .then(lambda x: x + 2)
            .then(lambda x: x / 2)
        )

        self.assertEqual(result, 11)
        self.assertIsNotNone(self.exception_ctx)
        self.assertIn("message", self.exception_ctx)

    async def test_resolve_disable_management(self):
        self.fut.set_result(10)
        result = (
            await Promise(self.fut, warn_no_management=False)
            .then(lambda x: x * 2)
            .then(lambda x: x + 2)
            .then(lambda x: x / 2)
        )

        self.assertEqual(result, 11)
        self.assertIsNone(self.exception_ctx)

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

    async def test_unexpected_exception(self):
        async def raise_exc():
            raise RuntimeError

        task = self.loop.create_task(raise_exc())

        Promise(task)

        with self.assertRaises(RuntimeError):
            await task

        self.assertIsNotNone(self.exception_ctx)
        self.assertIn("message", self.exception_ctx)
        self.assertIsInstance(self.exception_ctx["exception"], RuntimeError)

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
        self.assertFalse(p.cancelled())

    async def test_cancellation_lastly(self):
        temp = {}
        with Promise(self.fut) as p:
            p.cancel()

            with self.assertRaises(CancelledError):
                await p.then(lambda x: x * 2).lastly(lambda: temp.setdefault("lastly", 100))

        self.assertIn("lastly", temp)
        self.assertEqual(temp["lastly"], 100)

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
        self.assertIn("lastly", temp)

    async def test_chain_no_external_resolve(self):
        with Promise(self.fut) as p:
            t = p.then(lambda x: x * 2)

            with self.assertRaises(InvalidStateError):
                t.resolve(None)

            with self.assertRaises(InvalidStateError):
                t.reject(Exception())

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
            await p.notify_chain

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

    async def test_chain_cancellation_after_resolution(self):
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

            t1.cancel(chain=True)

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_after_resolution_3(self):
        with Promise(self.fut) as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

            t2 = t1.then(lambda x: sum_with_sleep(x, 10))

            p.cancel(chain=True)

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_sync_edge_case(self):
        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(lambda x: x * 2)
            self.assertEqual(await p, 10)

        with self.assertRaises(CancelledError):
            await p.notify_chain

        self.assertEqual(await t1, 20)

        t2 = t1.then(lambda x: sum_with_sleep(x, 10))

        with self.assertRaises(CancelledError):
            await t2

    async def test_task_cancellation_false(self):
        async def task(_):
            t1.cancel(task=False)
            await asleep(DEFAULT_SLEEP)
            return 0

        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(task)
            self.assertEqual(await t1, 0)

    async def test_task_cancellation_true(self):
        async def task(_):
            t1.cancel(task=True)
            await asleep(DEFAULT_SLEEP)
            return 0

        with Promise(self.fut) as p:
            p.resolve(10)
            t1 = p.then(task)
            with self.assertRaises(CancelledError):
                await t1


if __name__ == "__main__":
    unittest.main()
