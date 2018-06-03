import unittest

from destructify import Structure, BitField, FixedLengthField, StructureField


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


class StructureFieldTest(unittest.TestCase):
    def test_parsing(self):
        class Struct1(Structure):
            byte1 = FixedLengthField(length=1)
            byte2 = FixedLengthField(length=1)

        class Struct2(Structure):
            s1 = StructureField(Struct1)
            s2 = StructureField(Struct1)

        s = Struct2.from_bytes(b"\x01\x02\03\x04")
        self.assertEqual(b"\x01", s.s1.byte1)
        self.assertEqual(b"\x02", s.s1.byte2)
        self.assertEqual(b"\x03", s.s2.byte1)
        self.assertEqual(b"\x04", s.s2.byte2)

    def test_writing(self):
        class Struct1(Structure):
            byte1 = FixedLengthField(length=1)
            byte2 = FixedLengthField(length=1)

        class Struct2(Structure):
            s1 = StructureField(Struct1)
            s2 = StructureField(Struct1)

        s = Struct2()
        s.s1.byte1 = b"\x01"
        s.s1.byte2 = b"\x02"
        s.s2.byte1 = b"\x03"
        s.s2.byte2 = b"\x04"
        self.assertEqual(b"\x01\x02\03\x04", s.to_bytes())
