# Internal
import unittest
from asyncio import CancelledError

# External
import asynctest
from prop import Promise


@asynctest.strict
class TestPromiseChain(asynctest.TestCase, unittest.TestCase):
    async def test_cancellation_managed(self):
        with Promise() as p:
            t = p.then(lambda x: x * 2)
            t.cancel()

            with self.assertRaises(CancelledError):
                await t

        self.assertTrue(t.done())
        self.assertTrue(t.cancelled())

        self.assertTrue(p.done())
        self.assertTrue(p.cancelled())

    async def test_cancellation_managed_2(self):
        with Promise() as p:
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
