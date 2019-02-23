import unittest

from destructify import Structure, IntField, StructField
from tests import DestructifyTestCase


class StructFieldTest(DestructifyTestCase):
    def test_basic(self):
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x01020304, StructField(">I", multibyte=False))
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x04030201, StructField("<I", multibyte=False))
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x01020304, StructField("I", byte_order='big', multibyte=False))
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x01020304, StructField("<I", byte_order='big', multibyte=False))

    def test_multibyte(self):
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", (0x04030201,), StructField("<I", multibyte=True))
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04\x01\x02\x03\x04", (0x04030201, 0x04030201),
                                    StructField("<II", multibyte=True))

    def test_subclass(self):
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x04030201, IntField(byte_order='little'))
        self.assertFieldStreamEqual(b"\x01\x02\x03\x04", 0x01020304, IntField(byte_order='big'))

    def test_endianness_from_structure(self):
        class TestStructure(Structure):
            field3 = IntField(default=lambda s: s.field)

            class Meta:
                byte_order = 'little'

        self.assertStructureStreamEqual(b"\x01\x02\x03\x04", TestStructure(field3=0x04030201))

        class TestStructure2(Structure):
            field3 = IntField(default=lambda s: s.field)

            class Meta:
                byte_order = 'big'

        self.assertStructureStreamEqual(b"\x01\x02\x03\x04", TestStructure2(field3=0x01020304))
