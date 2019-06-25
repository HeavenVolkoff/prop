# Internal
import unittest

# External
import asynctest
from prop import Promise


# noinspection PyAttributeOutsideInit
@asynctest.strict
class TestPromiseFuture(asynctest.TestCase, unittest.TestCase):
    async def test_promise_chain_stack(self):
        p = Promise()

        self.assertEqual(len(p._stack), 1)
        self.assertEqual(p._stack[0].line, "p = Promise()")
        self.assertEqual(p._stack[0].lineno, 13)

        c1_1 = p.lastly(lambda: 1)

        self.assertEqual(len(c1_1._stack), 2)
        self.assertEqual(c1_1._stack[0], p._stack[0])
        self.assertEqual(c1_1._stack[1].line, "c1_1 = p.lastly(lambda: 1)")
        self.assertEqual(c1_1._stack[1].lineno, 19)

        c1_2 = c1_1.then(
            lambda _: "LongTextToPurposelyBeLargerThenTheCharacterLimitOfBlackWhichIsCurrently99"
        )

        self.assertEqual(len(c1_2._stack), 3)
        self.assertEqual(c1_2._stack[0], p._stack[0])
        self.assertEqual(c1_2._stack[1], c1_1._stack[1])
        self.assertEqual(
            c1_2._stack[2].line,
            'lambda _: "LongTextToPurposelyBeLargerThenTheCharacterLimitOfBlackWhichIsCurrently99"',
        )
        self.assertEqual(c1_2._stack[2].lineno, 27)

        c1_3 = c1_2.catch(lambda _: 3)

        self.assertEqual(len(c1_3._stack), 4)
        self.assertEqual(c1_3._stack[0], p._stack[0])
        self.assertEqual(c1_3._stack[1], c1_1._stack[1])
        self.assertEqual(c1_3._stack[2], c1_2._stack[2])
        self.assertEqual(c1_3._stack[3].line, "c1_3 = c1_2.catch(lambda _: 3)")
        self.assertEqual(c1_3._stack[3].lineno, 39)

        c2_1 = p.then(lambda _: 10)

        self.assertEqual(len(c2_1._stack), 2)
        self.assertEqual(c2_1._stack[0], p._stack[0])
        self.assertEqual(c2_1._stack[1].line, "c2_1 = p.then(lambda _: 10)")
        self.assertEqual(c2_1._stack[1].lineno, 48)

        c2_2 = c2_1.lastly(lambda: 20)

        self.assertEqual(len(c2_2._stack), 3)
        self.assertEqual(c2_2._stack[0], p._stack[0])
        self.assertEqual(c2_2._stack[1], c2_1._stack[1])
        self.assertEqual(c2_2._stack[2].line, "c2_2 = c2_1.lastly(lambda: 20)")
        self.assertEqual(c2_2._stack[2].lineno, 55)

        c2_3 = c2_2.then(lambda _: 30)

        self.assertEqual(len(c2_3._stack), 4)
        self.assertEqual(c2_3._stack[0], p._stack[0])
        self.assertEqual(c2_3._stack[1], c2_1._stack[1])
        self.assertEqual(c2_3._stack[2], c2_2._stack[2])
        self.assertEqual(c2_3._stack[3].line, "c2_3 = c2_2.then(lambda _: 30)")
        self.assertEqual(c2_3._stack[3].lineno, 63)

        p.resolve(None)
        self.assertEqual(
            await c1_3, "LongTextToPurposelyBeLargerThenTheCharacterLimitOfBlackWhichIsCurrently99"
        )
        self.assertEqual(await c2_3, 30)


if __name__ == "__main__":
    unittest.main()
