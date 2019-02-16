import unittest

from destructify import Structure, BitField, FixedLengthField, StructureField, MisalignedFieldError, ArrayField, \
    DefinitionError, BaseFieldMixin, Field


class BaseFieldTestCase(unittest.TestCase):
    def test_wrong_initialization(self):
        class MyField(BaseFieldMixin, Field):
            pass

        class Struct(Structure):
            pass

        with self.assertRaises(DefinitionError):
            MyField(Struct)
        with self.assertRaises(DefinitionError):
            MyField(Struct())
        with self.assertRaises(DefinitionError):
            MyField(BitField)

    def test_full_name_and_bound_structure(self):
        class MyField(BaseFieldMixin, Field):
            pass

        class Struct(Structure):
            thing = MyField(BitField(1))

        self.assertEqual("thing", Struct._meta.fields[0].base_field.name)
        self.assertEqual("Struct.thing", Struct._meta.fields[0].base_field.full_name)
        self.assertIs(Struct._meta.fields[0].bound_structure, Struct._meta.fields[0].base_field.bound_structure)


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

        self.assertEqual(b"\xFF\xe0", Struct(bit1=0b111, bit2=0b11111111).to_bytes())

    def test_writing_full_bytes(self):
        class Struct(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=5)

        self.assertEqual(b"\xFF", Struct(bit1=0b111, bit2=0b111111).to_bytes())

        class Struct2(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=5)
            byte = FixedLengthField(length=1)

        self.assertEqual(b"\xFF\x33", Struct2(bit1=0b111, bit2=0b111111, byte=b'\x33').to_bytes())

    def test_misaligned_field(self):
        class Struct(Structure):
            bit1 = BitField(length=1)
            bit2 = BitField(length=1)
            byte = FixedLengthField(length=1)

        with self.assertRaises(MisalignedFieldError):
            Struct.from_bytes(b"\xFF\xFF")

        with self.assertRaises(MisalignedFieldError):
            self.assertEqual(b"\xc0\x33", Struct(bit1=1, bit2=1, byte=b'\x33').to_bytes())

    def test_misaligned_field_with_realign(self):
        class Struct(Structure):
            bit1 = BitField(length=1)
            bit2 = BitField(length=1, realign=True)
            byte = FixedLengthField(length=1)

        s = Struct.from_bytes(b"\xFF\xFF")
        self.assertEqual(s.bit1, 1)
        self.assertEqual(s.bit2, 1)
        self.assertEqual(s.byte, b'\xFF')

        self.assertEqual(b"\xc0\x33", Struct(bit1=1, bit2=1, byte=b'\x33').to_bytes())


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
