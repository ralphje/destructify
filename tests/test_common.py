import enum
import unittest

from destructify import Structure, BitField, FixedLengthField, StructureField, MisalignedFieldError, ArrayField, \
    DefinitionError, BaseFieldMixin, Field, EnumField, FixedLengthStringField, TerminatedStringField, IntegerField


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


class StringFieldsTest(unittest.TestCase):
    def test_parsing_fixed_length(self):
        class Struct(Structure):
            string = FixedLengthStringField(5)

        class Struct2(Structure):
            string = FixedLengthStringField(8, encoding='utf-16-le')

        self.assertEqual('abcde', Struct.from_bytes(b"abcde").string)
        self.assertEqual('\xfcber', Struct2.from_bytes(b'\xfc\0b\0e\0r\0').string)

    def test_parsing_fixed_length_error(self):
        with self.assertRaises(UnicodeDecodeError):
            FixedLengthStringField(7, encoding='utf-16-le').from_bytes(b'\xfc\0b\0e\0r')

        self.assertEqual("\xfcbe\uFFFD",
                         FixedLengthStringField(7, encoding='utf-16-le', errors='replace').from_bytes(b'\xfc\0b\0e\0r'))
        self.assertEqual("h\0\0",
                         FixedLengthStringField(7, encoding='utf-16-le').from_bytes(b'h\0\0\0\0\0'))

    def test_writing_fixed_length(self):
        self.assertEqual(b"b\0y\0e\0b\0y\0e\0", FixedLengthStringField(7, encoding='utf-16-le').to_bytes("byebye"))

    def test_parsing_terminated(self):
        class Struct(Structure):
            string = TerminatedStringField(b'\0')

        class Struct2(Structure):
            string = TerminatedStringField(b'\0\0', encoding='utf-16-le', step=2)

        self.assertEqual('abcde', Struct.from_bytes(b"abcde\0").string)
        self.assertEqual('\xfcber', Struct2.from_bytes(b'\xfc\0b\0e\0r\0\0\0').string)

    def test_writing_terminated(self):
        self.assertEqual(b"b\0y\0e\0\0\0", TerminatedStringField(b'\0\0', encoding='utf-16-le').to_bytes("bye"))


class IntegerFieldTest(unittest.TestCase):
    def test_parsing(self):
        self.assertEqual(256, IntegerField(2, 'big').from_bytes(b'\x01\0'))
        self.assertEqual(1, IntegerField(2, 'little').from_bytes(b'\x01\0'))
        self.assertEqual(-257, IntegerField(2, 'little', signed=True).from_bytes(b'\xff\xfe'))
        self.assertEqual(65534, IntegerField(2, 'big', signed=False).from_bytes(b'\xff\xfe'))
        self.assertEqual(-257, IntegerField(2, 'big', signed=True).from_bytes(b'\xfe\xff'))

    def test_writing(self):
        self.assertEqual(b'\x01\0', IntegerField(2, 'big').to_bytes(256))
        self.assertEqual(b'\x01\0', IntegerField(2, 'little').to_bytes(1))
        self.assertEqual(b'\xff\xfe', IntegerField(2, 'little', signed=True).to_bytes(-257))
        with self.assertRaises(OverflowError):
            IntegerField(1, 'little').to_bytes(1000)
        with self.assertRaises(OverflowError):
            IntegerField(1, 'little').to_bytes(-1000)


class EnumFieldTest(unittest.TestCase):
    def test_len(self):
        self.assertEqual(1, len(EnumField(FixedLengthField(1), enum.Enum)))

    def test_parsing(self):
        class En(enum.Enum):
            TEST = b'b'

        class Struct(Structure):
            byte1 = EnumField(FixedLengthField(1), En)

        s = Struct.from_bytes(b"b")
        self.assertEqual(En.TEST, s.byte1)

        with self.assertRaises(ValueError):
            Struct.from_bytes(b'a')

    def test_writing(self):
        class En(enum.Enum):
            TEST = b'b'

        class Struct(Structure):
            byte1 = EnumField(FixedLengthField(1), En)

        s = Struct(byte1=En.TEST)
        self.assertEqual(b'b', s.to_bytes())

