import unittest

from destructify import Structure, IntField, StructField, CharField, ByteField, UnsignedByteField, BoolField, \
    ShortField, UnsignedShortField, UnsignedIntField, LongField, UnsignedLongField, LongLongField, \
    UnsignedLongLongField, SizeField, UnsignedSizeField, HalfPrecisionFloatField, FloatField, DoubleField, struct
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


class StructSubclassTest(DestructifyTestCase):
    def test_basic(self):
        self.assertFieldStreamEqual(b"\x01", b"\x01", CharField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff", -1, ByteField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff", 255, UnsignedByteField(byte_order='big'))
        self.assertFieldStreamEqual(b"\x01", 1, BoolField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff", -1, ShortField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff", 0xffff, UnsignedShortField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff", -1, IntField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff", 0xffffffff, UnsignedIntField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff", -1, LongField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff", 0xffffffff, UnsignedLongField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff\xff\xff\xff\xff", -1, LongLongField(byte_order='big'))
        self.assertFieldStreamEqual(b"\xff\xff\xff\xff\xff\xff\xff\xff", 0xffffffffffffffff,
                                    UnsignedLongLongField(byte_order='big'))
        self.assertFieldStreamEqual(b"J ", 12.25, HalfPrecisionFloatField(byte_order='big'))
        self.assertFieldStreamEqual(b"AD\x00\x00", 12.25, FloatField(byte_order='big'))
        self.assertFieldStreamEqual(b"@(\x80\x00\x00\x00\x00\x00", 12.25, DoubleField(byte_order='big'))

    def test_native(self):
        self.assertFieldStreamEqual(struct.pack("@n", 0xffffff), 0xffffff, SizeField(byte_order='native'))
        self.assertFieldStreamEqual(struct.pack("@N", 0xffffff), 0xffffff, UnsignedSizeField(byte_order='native'))
