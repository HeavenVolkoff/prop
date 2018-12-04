# Internal
import unittest
from asyncio import sleep

# External
import asynctest
from prop import Promise

SUCCESS_RESULT = 10


async def success_sleep():
    await sleep(0.05)
    return SUCCESS_RESULT


async def exception_sleep():
    await sleep(0.05)
    raise RuntimeError("Test")


# noinspection PyAttributeOutsideInit
@asynctest.strict
class TestPromiseCoro(asynctest.TestCase, unittest.TestCase):
    async def test_internal_state(self):
        promise = Promise(success_sleep(), loop=self.loop)
        self.assertEqual(promise.loop, self.loop)
        self.assertEqual(promise.done(), False)
        self.assertEqual(promise.cancelled(), False)

        await promise

        self.assertEqual(promise.loop, self.loop)
        self.assertEqual(promise.done(), True)
        self.assertEqual(promise.cancelled(), False)

    async def test_coro_missing_loop(self):
        coro = success_sleep()
        await Promise(coro)

    async def test_coro_success(self):
        self.assertEqual(await Promise(success_sleep(), loop=self.loop), SUCCESS_RESULT)

    async def test_coro_exception(self):
        with self.assertRaises(RuntimeError):
            await Promise(exception_sleep(), loop=self.loop)


if __name__ == "__main__":
    unittest.main()
