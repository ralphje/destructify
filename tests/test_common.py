import unittest

from destructify import Structure, BitField, FixedLengthField


class BitFieldTestCase(unittest.TestCase):
    def test_parsing(self):
        class Struct(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=8)

        s = Struct.from_bytes(b"\xFF\xFF")
        self.assertEqual(s.bit1, 0b111)
        self.assertEqual(s.bit2, 0b11111111)

    def test_writing(self):
        class Struct(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=8)

        self.assertEqual(Struct(bit1=0b111, bit2=0b11111111).to_bytes(), b"\xFF\xe0")

    def test_writing_full_bytes(self):
        class Struct(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=5)

        self.assertEqual(Struct(bit1=0b111, bit2=0b111111).to_bytes(), b"\xFF")

        class Struct2(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=5)
            byte = FixedLengthField(length=1)

        self.assertEqual(Struct2(bit1=0b111, bit2=0b111111, byte=b'\x33').to_bytes(), b"\xFF\x33")

