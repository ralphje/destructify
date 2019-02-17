import unittest

from destructify import Structure, BitField, FixedLengthField, StructureField, MisalignedFieldError, \
    FixedLengthStringField, TerminatedStringField, IntegerField, TerminatedField
from destructify.exceptions import DefinitionError, StreamExhaustedError, WriteError
from tests import DestructifyTestCase


class FixedLengthFieldTestCase(unittest.TestCase):
    def test_parsing(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=3)
            str2 = FixedLengthField(length=1)

        s = Struct.from_bytes(b"abcd")
        self.assertEqual(b"abc", s.str1)
        self.assertEqual(b"d", s.str2)

    def test_parsing_with_length_from_other_field(self):
        class Struct(Structure):
            len = IntegerField(length=1, byte_order='little')
            str1 = FixedLengthField(length='len')

        s = Struct.from_bytes(b"\x01a")
        self.assertEqual(1, s.len)
        self.assertEqual(b'a', s.str1)
        s = Struct.from_bytes(b"\x02ab")
        self.assertEqual(2, s.len)
        self.assertEqual(b'ab', s.str1)

    def test_parsing_with_too_little_bytes(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=3)

        with self.assertRaises(StreamExhaustedError):
            Struct.from_bytes(b"ab")

        class Struct2(Structure):
            str1 = FixedLengthField(length=3, strict=False)

        self.assertEqual(b"ab", Struct2.from_bytes(b"ab").str1)

    def test_writing(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=3)

        with self.assertRaises(WriteError):
            Struct(str1=b'hello').to_bytes()
        with self.assertRaises(WriteError):
            Struct(str1=b'he').to_bytes()
        self.assertEqual(b'hey', Struct(str1=b'hey').to_bytes())

        class Struct2(Structure):
            str1 = FixedLengthField(length=3, strict=False)
        self.assertEqual(b'hel', Struct2(str1=b'hello').to_bytes())

    def test_writing_with_length_from_other_field(self):
        class Struct(Structure):
            len = IntegerField(length=1, byte_order='little')
            str1 = FixedLengthField(length='len')

        self.assertEqual(b'\x05hello', Struct(str1=b'hello').to_bytes())
        self.assertEqual(b'\x01h', Struct(len=1, str1=b'h').to_bytes())

    def test_writing_with_length_from_other_field_that_has_override(self):
        class Struct(Structure):
            len = IntegerField(length=1, byte_order='little', override=lambda c, v: v)
            str1 = FixedLengthField(length='len')

        self.assertEqual(b'\x05hello', Struct(len=5, str1=b'hello').to_bytes())

        with self.assertRaises(Exception):
            Struct(str1=b'hello').to_bytes()

    def test_parsing_with_padding(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=10, padding=b'\0')

        self.assertEqual(b'hello', Struct.from_bytes(b"hello\0\0\0\0\0").str1)
        self.assertEqual(b'hello\0\0\0\0\x01', Struct.from_bytes(b"hello\0\0\0\0\x01").str1)

        class Struct2(Structure):
            str1 = FixedLengthField(length=10, padding=b'\x01\x02')

        self.assertEqual(b'hello\0', Struct2.from_bytes(b"hello\0\x01\x02\x01\x02").str1)
        self.assertEqual(b'hello\0\x01\x02\x01a', Struct2.from_bytes(b"hello\0\x01\x02\x01a").str1)

    def test_writing_with_padding(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=10, padding=b'\0')

        self.assertEqual(b'hello\0\0\0\0\0', Struct(str1=b"hello").to_bytes())
        self.assertEqual(b'hellohello', Struct(str1=b"hellohello").to_bytes())

        class Struct2(Structure):
            str1 = FixedLengthField(length=10, padding=b'\x01\x02')

        self.assertEqual(b'hello\0\x01\x02\x01\x02', Struct2(str1=b"hello\0").to_bytes())
        with self.assertRaises(WriteError):
            Struct2(str1=b"hello").to_bytes()
        with self.assertRaises(WriteError):
            Struct2(str1=b"hellohellohello").to_bytes()

    def test_writing_with_padding_not_strict(self):
        class Struct2(Structure):
            str1 = FixedLengthField(length=10, padding=b'\x01\x02', strict=False)

        self.assertEqual(b'hello\x01\x02\x01\x02\x01', Struct2(str1=b"hello").to_bytes())
        self.assertEqual(b'hellohello', Struct2(str1=b"hellohellohello").to_bytes())

    def test_writing_and_parsing_with_padding_zero_length(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=0, padding=b'\0')

        self.assertEqual(b'', Struct.from_bytes(b'asdf').str1)
        self.assertEqual(b'', Struct(str1=b"").to_bytes())

    def test_writing_and_parsing_negative_length(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=-1)

        self.assertEqual(b'asdf', Struct.from_bytes(b'asdf').str1)
        self.assertEqual(b'asdf', Struct(str1=b"asdf").to_bytes())

    def test_writing_and_parsing_negative_length_and_padding(self):
        class Struct(Structure):
            str1 = FixedLengthField(length=-1, padding=b'\0')

        self.assertEqual(b'asdf', Struct.from_bytes(b'asdf').str1)
        self.assertEqual(b'asdf', Struct(str1=b"asdf").to_bytes())


class TerminatedFieldTest(DestructifyTestCase):
    def test_simple_terminator(self):
        self.assertFromStreamEqual(b"asdfasdf", TerminatedField(terminator=b'\0'), b'asdfasdf\0')
        self.assertFromStreamEqual(b"", TerminatedField(terminator=b'\0'), b'\0')
        with self.assertRaises(StreamExhaustedError):
            self.call_from_stream(TerminatedField(terminator=b'\0'), b'asdfasdf')

        self.assertToStreamEqual(b"\0", TerminatedField(terminator=b'\0'), b'')
        self.assertToStreamEqual(b"asdf\0", TerminatedField(terminator=b'\0'), b'asdf')

    def test_multibyte_terminator(self):
        self.assertFromStreamEqual(b"asdfasdf", TerminatedField(terminator=b'\0\x91'), b'asdfasdf\0\x91')
        self.assertFromStreamEqual(b"", TerminatedField(terminator=b'\0\x91'), b'\0\x91')

        self.assertToStreamEqual(b"\0\x91", TerminatedField(terminator=b'\0\x91'), b'')
        self.assertToStreamEqual(b"asdf\0\x91", TerminatedField(terminator=b'\0\x91'), b'asdf')

    def test_multibyte_terminator_aligned(self):
        self.assertFromStreamEqual(b"asdfasdf", TerminatedField(terminator=b'\0\0', step=2), b'asdfasdf\0\0')
        with self.assertRaises(StreamExhaustedError):
            self.call_from_stream(TerminatedField(terminator=b'\0\0', step=2), b'asdfasd\0\0')


class BitFieldTest(unittest.TestCase):
    def test_parsing(self):
        class Struct(Structure):
            bit1 = BitField(length=3)
            bit2 = BitField(length=8)

        s = Struct.from_bytes(b"\xFF\xFF")
        self.assertEqual(0b111, s.bit1)
        self.assertEqual(0b11111111, s.bit2)

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
        self.assertEqual(1, s.bit1)
        self.assertEqual(1, s.bit2)
        self.assertEqual(b'\xFF', s.byte)

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

    def test_unlimited_substructure(self):
        class UnlimitedFixedLengthStructure(Structure):
            text = FixedLengthField(length=-1)

        class UFLSStructure(Structure):
            s = StructureField(UnlimitedFixedLengthStructure, length=5)

        ufls = UnlimitedFixedLengthStructure.from_bytes(b"\x01\x02\x03\x04\x05")
        self.assertEqual(b"\x01\x02\x03\x04\x05", ufls.text)
        ufls = UFLSStructure.from_bytes(b"\x01\x02\x03\x04\x05\x06")
        self.assertEqual(b"\x01\x02\x03\x04\x05", ufls.s.text)

    def test_structure_that_skips_bytes(self):
        class ShortStructure(Structure):
            text = FixedLengthField(length=3)

        class StructureThatSkips(Structure):
            s = StructureField(ShortStructure, length=5)
            text = FixedLengthField(length=3)

        s = StructureThatSkips.from_bytes(b"\x01\x02\x03\x04\x05\x06\x07\x08")
        self.assertEqual(b"\x01\x02\x03", s.s.text)
        self.assertEqual(b"\x06\x07\x08", s.text)


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


class IntegerFieldTest(DestructifyTestCase):
    def test_parsing(self):
        self.assertEqual(256, IntegerField(2, 'big').from_bytes(b'\x01\0'))
        self.assertEqual(1, IntegerField(2, 'little').from_bytes(b'\x01\0'))
        self.assertEqual(-257, IntegerField(2, 'little', signed=True).from_bytes(b'\xff\xfe'))
        self.assertEqual(65534, IntegerField(2, 'big', signed=False).from_bytes(b'\xff\xfe'))
        self.assertEqual(-257, IntegerField(2, 'big', signed=True).from_bytes(b'\xfe\xff'))

    def test_writing(self):
        self.assertToStreamEqual(b'\x01\0', IntegerField(2, 'big'), 256)
        self.assertToStreamEqual(b'\x01\0', IntegerField(2, 'little'), 1)
        self.assertToStreamEqual(b'\xff\xfe', IntegerField(2, 'little', signed=True), -257)
        with self.assertRaises(OverflowError):
            self.assertToStreamEqual(None, IntegerField(1, 'little'), 1000)
        with self.assertRaises(OverflowError):
            self.assertToStreamEqual(None, IntegerField(1, 'little'), -1000)

    def test_parsing_with_byte_order_on_structure(self):
        with self.assertRaises(DefinitionError):
            class Struct(Structure):
                num = IntegerField(2)

        class Struct2(Structure):
            num = IntegerField(2)
            class Meta:
                byte_order = 'little'

        self.assertEqual(513, Struct2.from_bytes(b"\x01\x02").num)

        class Struct3(Structure):
            num = IntegerField(2)
            class Meta:
                byte_order = 'big'

        self.assertEqual(258, Struct3.from_bytes(b"\x01\x02").num)

    def test_parsing_and_writing_without_byte_order_single_byte(self):
        class Struct(Structure):
            num = IntegerField(1)

        self.assertEqual(1, Struct.from_bytes(b"\x01").num)
        self.assertEqual(b'\x01', Struct(num=1).to_bytes())
