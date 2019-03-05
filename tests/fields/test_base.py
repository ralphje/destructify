import unittest

from destructify import Structure, IntField, StructField, DefinitionError, Field, FixedLengthField
from tests import DestructifyTestCase


class FieldTest(DestructifyTestCase):
    def test_initialize_offset_skip(self):
        self.assertEqual(3, Field(offset=3).offset)
        with self.assertRaises(DefinitionError):
            Field(offset=3, skip=3)
        with self.assertRaises(DefinitionError):
            Field(skip=-3)

    def test_aligned_field(self):
        def align(a):
            class Struct(Structure):
                f1 = FixedLengthField(2)
                f2 = FixedLengthField(1)
                f3 = FixedLengthField(3)

                class Meta:
                    alignment = a
            return Struct

        self.assertStructureStreamEqual(b"12\0\0a\0\0\0bbb", align(4)(f1=b'12', f2=b'a', f3=b'bbb'))
        self.assertStructureStreamEqual(b"12abbb", align(1)(f1=b'12', f2=b'a', f3=b'bbb'))
        self.assertStructureStreamEqual(b"12a\0bbb", align(2)(f1=b'12', f2=b'a', f3=b'bbb'))

    def test_aligned_field_with_skip(self):
        def align(a):
            class Struct(Structure):
                f1 = FixedLengthField(2)
                f2 = FixedLengthField(1, skip=0)
                f3 = FixedLengthField(3)

                class Meta:
                    alignment = a
            return Struct

        self.assertStructureStreamEqual(b"12a\0bbb", align(4)(f1=b'12', f2=b'a', f3=b'bbb'))
