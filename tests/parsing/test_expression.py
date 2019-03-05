import unittest

from destructify import this


class AttributeAccess:
    one = 1
    two = 2
    three = 3
    list = [1, 2]


class FTest(unittest.TestCase):
    obj = AttributeAccess()

    def test_simple_access(self):
        self.assertEqual(1, this.one(self.obj))
        self.assertEqual(2, this.two(self.obj))

    def test_comparison_both(self):
        self.assertTrue((this.one < this.two)(self.obj))
        self.assertTrue((this.one <= this.two)(self.obj))
        self.assertTrue((this.one == this.one)(self.obj))
        self.assertTrue((this.one != this.two)(self.obj))
        self.assertTrue((this.two > this.one)(self.obj))
        self.assertTrue((this.two >= this.one)(self.obj))

        self.assertFalse((this.one > this.two)(self.obj))
        self.assertFalse((this.one >= this.two)(self.obj))
        self.assertFalse((this.one == this.two)(self.obj))
        self.assertFalse((this.one != this.one)(self.obj))
        self.assertFalse((this.two < this.one)(self.obj))
        self.assertFalse((this.two <= this.one)(self.obj))

    def test_comparison_one(self):
        self.assertTrue((this.one < 2)(self.obj))
        self.assertTrue((this.one <= 2)(self.obj))
        self.assertTrue((this.one == 1)(self.obj))
        self.assertTrue((this.one != 2)(self.obj))
        self.assertTrue((this.two > 1)(self.obj))
        self.assertTrue((this.two >= 1)(self.obj))

        self.assertTrue((1 < this.two)(self.obj))
        self.assertTrue((1 <= this.two)(self.obj))
        self.assertTrue((1 == this.one)(self.obj))
        self.assertTrue((1 != this.two)(self.obj))
        self.assertTrue((2 > this.one)(self.obj))
        self.assertTrue((1 >= this.one)(self.obj))

    def test_math_both(self):
        self.assertEqual(3, (this.one + this.two)(self.obj))
        self.assertEqual(-1, (this.one - this.two)(self.obj))
        self.assertEqual(2, (this.one * this.two)(self.obj))
        self.assertEqual(1 / 2, (this.one / this.two)(self.obj))
        # TODO: matmul
        self.assertEqual(0, (this.one // this.two)(self.obj))
        self.assertEqual(1, (this.three % this.two)(self.obj))
        self.assertEqual((1, 1), divmod(this.three, this.two)(self.obj))
        self.assertEqual(9, (this.three ** this.two)(self.obj))
        self.assertEqual(9, (this.three ** this.two)(self.obj))
        self.assertEqual(4, (this.two << this.one)(self.obj))
        self.assertEqual(1, (this.two >> this.one)(self.obj))
        self.assertEqual(1, (this.three & this.one)(self.obj))
        self.assertEqual(2, (this.three ^ this.one)(self.obj))
        self.assertEqual(3, (this.two | this.one)(self.obj))

    def test_math_one(self):
        self.assertEqual(3, (1 + this.two)(self.obj))
        self.assertEqual(-1, (1 - this.two)(self.obj))
        self.assertEqual(2, (1 * this.two)(self.obj))
        self.assertEqual(1 / 2, (1 / this.two)(self.obj))
        # TODO: matmul
        self.assertEqual(0, (1 // this.two)(self.obj))
        self.assertEqual(1, (3 % this.two)(self.obj))
        self.assertEqual((1, 1), divmod(3, this.two)(self.obj))
        self.assertEqual(9, (3 ** this.two)(self.obj))
        self.assertEqual(9, (3 ** this.two)(self.obj))
        self.assertEqual(4, (2 << this.one)(self.obj))
        self.assertEqual(1, (2 >> this.one)(self.obj))
        self.assertEqual(1, (3 & this.one)(self.obj))
        self.assertEqual(2, (3 ^ this.one)(self.obj))
        self.assertEqual(3, (2 | this.one)(self.obj))

    def test_unary(self):
        self.assertEqual(-1, (-this.one)(self.obj))
        self.assertEqual(2, (+this.two)(self.obj))
        self.assertEqual(1, (abs(this.one))(self.obj))
        self.assertEqual(-2, (~this.one)(self.obj))
