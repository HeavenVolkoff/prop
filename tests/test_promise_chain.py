# Internal
import unittest
from asyncio import CancelledError, sleep as asleep
from collections import Counter

# External
import asynctest
from prop import Promise

DEFAULT_SLEEP = 0.05


async def sum_with_sleep(x, y):
    await asleep(DEFAULT_SLEEP)
    return x + y


async def division_by_0():
    return 1 / 0


UNIQUE = object()


# noinspection PyAttributeOutsideInit
@asynctest.strict
class TestPromiseChain(asynctest.TestCase, unittest.TestCase):
    async def test_resolve_1(self):
        self.assertTrue(await Promise().resolve(True))

    async def test_resolve_2(self):
        self.assertIs(await Promise().resolve(UNIQUE), UNIQUE)

    async def test_resolve_3(self):
        self.assertIsInstance(await Promise().resolve(RuntimeError()), RuntimeError)

    async def test_reject_exception(self):
        with self.assertRaises(RuntimeError):
            await Promise().reject(RuntimeError())

    async def test_reject_base_exception(self):
        with self.assertRaises(GeneratorExit):
            await Promise().reject(GeneratorExit())

    async def test_reject_exception_type(self):
        with self.assertRaises(Exception):
            await Promise().reject(Exception)

    async def test_single_then_modify_data(self):
        self.assertEqual(await Promise().resolve(10).then(lambda x: x * 2), 20)

    async def test_single_then_replace_data(self):
        self.assertEqual(await Promise().resolve(10).then(lambda _: "Hello"), "Hello")

    async def test_multiple_then(self):
        self.assertEqual(
            await Promise()
            .resolve(10)
            .then(lambda x: x * 2)
            .then(lambda x: x + 2)
            .then(lambda x: x / 2),
            11,
        )

    async def test_then_chain_timing(self):
        p = Promise().resolve(10)
        start_time = self.loop.time()
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

        self.assertEqual(result, 100)
        self.assertAlmostEqual(DEFAULT_SLEEP * 9, end_time - start_time, delta=0.05)

    async def test_catch(self):
        p = Promise(division_by_0())

        with self.assertRaises(ZeroDivisionError):
            await p

        self.assertTrue(await p.catch(lambda exc: isinstance(exc, ZeroDivisionError)))

    async def test_catch_mid_chain(self):
        counter = Counter()
        p = Promise(division_by_0()).then(lambda num: counter.update(["then"]) or num + 10)

        with self.assertRaises(ZeroDivisionError):
            await p

        self.assertTrue(await p.catch(lambda exc: isinstance(exc, ZeroDivisionError)))
        self.assertEqual(counter["then"], 0)

    async def test_catch_continue_chain(self):
        counter = Counter()
        p = (
            Promise(division_by_0())
            .catch(lambda _: counter.update(["catch"]) or UNIQUE)
            .then(lambda val: counter.update(["then"]) or val is UNIQUE)
            .catch(lambda exc: counter.update(["catch"]))
        )

        self.assertTrue(await p)
        self.assertEqual(counter["catch"], 1)
        self.assertEqual(counter["then"], 1)

    async def test_catch_fails(self):
        counter = Counter()

        def fails_catch(prop_exc):
            self.assertIsInstance(prop_exc, ZeroDivisionError)
            counter.update(["catch"])
            raise RuntimeError

        try:
            await (Promise(division_by_0()).catch(fails_catch))
        except RuntimeError as exc:
            self.assertIsInstance(exc.__context__, ZeroDivisionError)
        else:
            self.fail("Promise should not have succeeded")

        self.assertEqual(counter["catch"], 1)

    async def test_catch_fails_and_recover(self):
        counter = Counter()

        def fails_catch(exc):
            self.assertIsInstance(exc, ZeroDivisionError)
            counter.update(["catch"])
            raise RuntimeError

        self.assertIs(
            await (
                Promise(division_by_0())
                .catch(fails_catch)
                .catch(
                    lambda exc: self.assertIsInstance(exc, RuntimeError)
                    or self.assertIsInstance(exc.__context__, ZeroDivisionError)
                    or counter.update(["catch"])
                    or UNIQUE
                )
            ),
            UNIQUE,
        )
        self.assertEqual(counter["catch"], 2)

    async def test_lastly_simple(self):
        counter = Counter()

        self.assertEqual(
            await Promise(sum_with_sleep(123, 321)).lastly(lambda: counter.update(["lastly"])), 444
        )
        self.assertEqual(counter["lastly"], 1)

    async def test_lastly_simple_error(self):
        counter = Counter()

        p = Promise(division_by_0()).lastly(lambda: counter.update(["lastly"]))

        with self.assertRaises(ZeroDivisionError):
            await p

        self.assertEqual(counter["lastly"], 1)

    async def test_promise_immediate_cancellation(self):
        p = Promise()
        counter = Counter()

        p.cancel()
        with self.assertRaises(CancelledError):
            await (
                p.then(lambda x: counter.update(["then"]))
                .catch(lambda exc: counter.update(["catch"]))
                .lastly(lambda: counter.update(["lastly"]))
            )

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())
        self.assertEqual(counter["then"], 0)
        self.assertEqual(counter["catch"], 0)
        self.assertEqual(counter["lastly"], 0)

    async def test_promise_cancellation_after_result(self):
        p = Promise()
        counter = Counter()

        p.cancel()
        with self.assertRaises(CancelledError):
            await (
                p.then(lambda x: counter.update(["then"]))
                .catch(lambda exc: counter.update(["catch"]))
                .lastly(lambda: counter.update(["lastly"]))
            )

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())
        self.assertEqual(counter["then"], 0)
        self.assertEqual(counter["catch"], 0)
        self.assertEqual(counter["lastly"], 0)

    async def test_chain_no_external_resolve(self):
        with Promise() as p:
            self.assertTrue(callable(getattr(p, "resolve")))
            self.assertTrue(callable(getattr(p, "reject")))

            t = p.then(lambda x: x * 2)

            self.assertFalse(hasattr(t, "resolve"))
            self.assertFalse(hasattr(t, "reject"))

            p.resolve(10)
            result = await t

        self.assertEqual(result, 20)

    async def test_chain_cancellation_sync(self):
        with Promise() as p:
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
        with Promise() as p:
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
        with Promise() as p:
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
        with Promise() as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

        t2 = t1.then(lambda x: sum_with_sleep(x, 10))

        with self.assertRaises(CancelledError):
            await t2

    async def test_chain_cancellation_after_resolution_2(self):
        with Promise() as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

            t2 = t1.then(lambda x: sum_with_sleep(x, 10))

            t1.cancel()

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_after_resolution_3(self):
        with Promise() as p:
            p.resolve(10)

            self.assertEqual(await p, 10)
            t1 = p.then(lambda x: x * 2)

            self.assertEqual(await t1, 20)

            t2 = t1.then(lambda x: sum_with_sleep(x, 10))

            p.cancel()

            with self.assertRaises(CancelledError):
                await t2

    async def test_chain_cancellation_sync_edge_case(self):
        with Promise() as p:
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

        with Promise() as p:
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

    @asynctest.fail_on(unused_loop=False)
    def test_base_exception(self):
        from asyncio import new_event_loop
        from prop._helper import fulfill

        loop = new_event_loop()

        fut = loop.create_future()
        fut.set_exception(KeyboardInterrupt)

        with self.assertRaises(KeyboardInterrupt):
            loop.run_until_complete(fulfill(fut, lambda: None))

        loop.close()


if __name__ == "__main__":
    unittest.main()
