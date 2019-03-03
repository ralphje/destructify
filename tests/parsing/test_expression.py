import unittest

from destructify import S


class AttributeAccess:
    one = 1
    two = 2
    three = 3
    list = [1, 2]


class FTest(unittest.TestCase):
    obj = AttributeAccess()

    def test_simple_access(self):
        self.assertEqual(1, S.one(self.obj))
        self.assertEqual(2, S.two(self.obj))

    def test_comparison_both(self):
        self.assertTrue((S.one < S.two)(self.obj))
        self.assertTrue((S.one <= S.two)(self.obj))
        self.assertTrue((S.one == S.one)(self.obj))
        self.assertTrue((S.one != S.two)(self.obj))
        self.assertTrue((S.two > S.one)(self.obj))
        self.assertTrue((S.two >= S.one)(self.obj))

        self.assertFalse((S.one > S.two)(self.obj))
        self.assertFalse((S.one >= S.two)(self.obj))
        self.assertFalse((S.one == S.two)(self.obj))
        self.assertFalse((S.one != S.one)(self.obj))
        self.assertFalse((S.two < S.one)(self.obj))
        self.assertFalse((S.two <= S.one)(self.obj))

    def test_comparison_one(self):
        self.assertTrue((S.one < 2)(self.obj))
        self.assertTrue((S.one <= 2)(self.obj))
        self.assertTrue((S.one == 1)(self.obj))
        self.assertTrue((S.one != 2)(self.obj))
        self.assertTrue((S.two > 1)(self.obj))
        self.assertTrue((S.two >= 1)(self.obj))

        self.assertTrue((1 < S.two)(self.obj))
        self.assertTrue((1 <= S.two)(self.obj))
        self.assertTrue((1 == S.one)(self.obj))
        self.assertTrue((1 != S.two)(self.obj))
        self.assertTrue((2 > S.one)(self.obj))
        self.assertTrue((1 >= S.one)(self.obj))

    def test_math_both(self):
        self.assertEqual(3, (S.one + S.two)(self.obj))
        self.assertEqual(-1, (S.one - S.two)(self.obj))
        self.assertEqual(2, (S.one * S.two)(self.obj))
        self.assertEqual(1 / 2, (S.one / S.two)(self.obj))
        # TODO: matmul
        self.assertEqual(0, (S.one // S.two)(self.obj))
        self.assertEqual(1, (S.three % S.two)(self.obj))
        self.assertEqual((1, 1), divmod(S.three, S.two)(self.obj))
        self.assertEqual(9, (S.three ** S.two)(self.obj))
        self.assertEqual(9, (S.three ** S.two)(self.obj))
        self.assertEqual(4, (S.two << S.one)(self.obj))
        self.assertEqual(1, (S.two >> S.one)(self.obj))
        self.assertEqual(1, (S.three & S.one)(self.obj))
        self.assertEqual(2, (S.three ^ S.one)(self.obj))
        self.assertEqual(3, (S.two | S.one)(self.obj))

    def test_math_one(self):
        self.assertEqual(3, (1 + S.two)(self.obj))
        self.assertEqual(-1, (1 - S.two)(self.obj))
        self.assertEqual(2, (1 * S.two)(self.obj))
        self.assertEqual(1 / 2, (1 / S.two)(self.obj))
        # TODO: matmul
        self.assertEqual(0, (1 // S.two)(self.obj))
        self.assertEqual(1, (3 % S.two)(self.obj))
        self.assertEqual((1, 1), divmod(3, S.two)(self.obj))
        self.assertEqual(9, (3 ** S.two)(self.obj))
        self.assertEqual(9, (3 ** S.two)(self.obj))
        self.assertEqual(4, (2 << S.one)(self.obj))
        self.assertEqual(1, (2 >> S.one)(self.obj))
        self.assertEqual(1, (3 & S.one)(self.obj))
        self.assertEqual(2, (3 ^ S.one)(self.obj))
        self.assertEqual(3, (2 | S.one)(self.obj))

    def test_unary(self):
        self.assertEqual(-1, (-S.one)(self.obj))
        self.assertEqual(2, (+S.two)(self.obj))
        self.assertEqual(1, (abs(S.one))(self.obj))
        self.assertEqual(-2, (~S.one)(self.obj))
