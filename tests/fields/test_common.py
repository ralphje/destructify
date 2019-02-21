import unittest

from destructify import Structure, BitField, FixedLengthField, StructureField, MisalignedFieldError, \
    StringField, IntegerField, TerminatedField, BytesField
from destructify.exceptions import DefinitionError, StreamExhaustedError, WriteError
from tests import DestructifyTestCase


class BytesFieldTestCase(DestructifyTestCase):
    def test_length(self):
        self.assertFieldStreamEqual(b"abc", b"abc", BytesField(length=3))
        self.assertFieldStreamEqual(b"", b"", BytesField(length=0))
        self.assertFieldFromStreamEqual(b"abcdef", b"abc", BytesField(length=3))

    def test_dynamic_length(self):
        self.assertFieldStreamEqual(b"abc", b"abc", BytesField(length='length'),
                                    parsed_fields={'length': 3})
        self.assertFieldStreamEqual(b"abc", b"abc", BytesField(length=lambda c: 3))

    def test_dynamic_length_full(self):
        class Struct(Structure):
            len = IntegerField(length=1, byte_order='little')
            str1 = BytesField(length='len')

        self.assertStructureStreamEqual(b'\x05hello', Struct(len=5, str1=b'hello'))
        self.assertEqual(b'\x05hello', Struct(str1=b'hello').to_bytes())
        self.assertEqual(b'\x01h', Struct(len=1, str1=b'h').to_bytes())

    def test_dynamic_length_full_other_field_has_override(self):
        class Struct(Structure):
            len = IntegerField(length=1, byte_order='little', override=lambda c, v: v)
            str1 = BytesField(length='len')

        self.assertEqual(b'\x05hello', Struct(len=5, str1=b'hello').to_bytes())

        with self.assertRaises(Exception):
            Struct(str1=b'hello').to_bytes()

    def test_length_insufficient_bytes(self):
        with self.assertRaises(StreamExhaustedError):
            self.call_field_from_stream(BytesField(length=8), b"abc")
        self.call_field_from_stream(BytesField(length=8, strict=False), b"abc")

    def test_length_and_padding(self):
        self.assertFieldStreamEqual(b"a\0\0\0\0\0\0\0", b"a", BytesField(length=8, padding=b"\0"))
        self.assertFieldStreamEqual(b"aXPADXPAD", b"a", BytesField(length=9, padding=b"XPAD"))
        self.assertFieldStreamEqual(b"abcd\0\0", b"abcd", BytesField(length=6, padding=b"\0\0", step=2))
        self.assertFieldStreamEqual(b"abc\0\0\0", b"abc\0", BytesField(length=6, padding=b"\0\0", step=2))
        self.assertFieldStreamEqual(b"abc\0\0\0\0", b"abc", BytesField(length=7, padding=b"\0\0"))

    def test_length_and_misaligned_padding(self):
        with self.assertRaises(WriteError):
            self.call_field_to_stream(BytesField(length=7, padding=b"\0\0"), b"ab")
        self.assertFieldToStreamEqual(b"ab\0\0\0\0\0", b"ab", BytesField(length=7, padding=b"\0\0", strict=False))

    def test_length_write_insufficient_bytes(self):
        with self.assertRaises(WriteError):
            self.call_field_to_stream(BytesField(length=7), b"ab")
        self.assertFieldToStreamEqual(b"ab", b"ab", BytesField(length=7, strict=False))

    def test_length_write_too_many_bytes(self):
        with self.assertRaises(WriteError):
            self.call_field_to_stream(BytesField(length=2), b"abcdefg")
        self.assertFieldToStreamEqual(b"ab", b"abcdefg", BytesField(length=2, strict=False))

    def test_negative_length(self):
        self.assertFieldStreamEqual(b"abc", b"abc", BytesField(length=-1))
        self.assertFieldStreamEqual(b"", b"", BytesField(length=-1))
        self.assertFieldStreamEqual(b"asd\0", b"asd", BytesField(length=-1, terminator=b"\0"))

    def test_terminator(self):
        self.assertFieldStreamEqual(b"abcdef\0", b"abcdef", BytesField(terminator=b"\0"))
        self.assertFieldFromStreamEqual(b"abc\0def", b"abc", BytesField(terminator=b"\0"))

    def test_terminator_insufficient_bytes(self):
        with self.assertRaises(StreamExhaustedError):
            self.call_field_from_stream(BytesField(terminator=b'\0'), b"abc")
        self.assertFieldFromStreamEqual(b"abc", b"abc", BytesField(terminator=b'\0', strict=False))

    def test_multibyte_terminator(self):
        self.assertFieldStreamEqual(b"abcdef\0\0", b"abcdef", BytesField(terminator=b"\0\0"))
        self.assertFieldFromStreamEqual(b"a\0bc\0\0def", b"a\0bc", BytesField(terminator=b"\0\0"))
        self.assertFieldStreamEqual(b"abcde\0\0\0", b"abcde\0", BytesField(terminator=b"\0\0", step=2))

    def test_length_and_terminator(self):
        self.assertFieldStreamEqual(b"abcdef\0", b"abcdef", BytesField(length=7, terminator=b"\0"))
        self.assertFieldFromStreamEqual(b"abc\0def", b"abc", BytesField(length=7, terminator=b"\0"))

    def test_length_and_terminator_insufficient_bytes(self):
        with self.assertRaises(StreamExhaustedError):
            self.call_field_from_stream(BytesField(terminator=b'\0', length=3), b"abc")
        with self.assertRaises(StreamExhaustedError):
            self.call_field_from_stream(BytesField(terminator=b'\0\0', length=3), b"abc")
        with self.assertRaises(StreamExhaustedError):
            self.call_field_from_stream(BytesField(terminator=b'\0', length=8), b"abc")
        self.assertFieldFromStreamEqual(b"abc", b"abc", BytesField(length=3, terminator=b'\0', strict=False))
        self.assertFieldFromStreamEqual(b"ab", b"ab", BytesField(length=3, terminator=b'\0', strict=False))

    def test_length_and_multibyte_terminator(self):
        self.assertFieldStreamEqual(b"abcdef\0\0", b"abcdef", BytesField(terminator=b"\0\0", length=8))
        self.assertFieldFromStreamEqual(b"a\0bc\0\0def", b"a\0bc", BytesField(terminator=b"\0\0", length=9))
        self.assertFieldStreamEqual(b"abcde\0\0\0", b"abcde\0", BytesField(terminator=b"\0\0", step=2, length=8))


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


class StringFieldTest(DestructifyTestCase):
    def test_fixed_length(self):
        self.assertFieldStreamEqual(b"abcde", 'abcde', StringField(length=5))
        self.assertFieldStreamEqual(b'\xfc\0b\0e\0r\0', '\xfcber', StringField(length=8, encoding='utf-16-le'))
        self.assertFieldStreamEqual(b'b\0y\0e\0b\0y\0e\0', 'byebye', StringField(length=12, encoding='utf-16-le'))

    def test_fixed_length_error(self):
        with self.assertRaises(UnicodeDecodeError):
            self.call_field_from_stream(StringField(length=7, encoding='utf-16-le'), b'\xfc\0b\0e\0r')

        self.assertFieldFromStreamEqual(b'\xfc\0b\0e\0r', "\xfcbe\uFFFD",
                                        StringField(length=7, encoding='utf-16-le', errors='replace'))
        self.assertFieldFromStreamEqual(b'h\0\0\0\0\0', "h\0\0",
                                        StringField(length=6, encoding='utf-16-le'))

    def test_terminated(self):
        self.assertFieldStreamEqual(b"abcde\0", 'abcde', StringField(terminator=b'\0'))
        self.assertFieldStreamEqual(b'b\0y\0e\0\0\0', 'bye', StringField(terminator=b'\0\0', step=2, encoding='utf-16-le'))


class IntegerFieldTest(DestructifyTestCase):
    def test_parsing(self):
        self.assertEqual(256, IntegerField(2, 'big').from_bytes(b'\x01\0'))
        self.assertEqual(1, IntegerField(2, 'little').from_bytes(b'\x01\0'))
        self.assertEqual(-257, IntegerField(2, 'little', signed=True).from_bytes(b'\xff\xfe'))
        self.assertEqual(65534, IntegerField(2, 'big', signed=False).from_bytes(b'\xff\xfe'))
        self.assertEqual(-257, IntegerField(2, 'big', signed=True).from_bytes(b'\xfe\xff'))

    def test_writing(self):
        self.assertFieldToStreamEqual(b'\x01\0', 256, IntegerField(2, 'big'))
        self.assertFieldToStreamEqual(b'\x01\0', 1, IntegerField(2, 'little'))
        self.assertFieldToStreamEqual(b'\xff\xfe', -257, IntegerField(2, 'little', signed=True))
        with self.assertRaises(OverflowError):
            self.assertFieldToStreamEqual(None, 1000, IntegerField(1, 'little'))
        with self.assertRaises(OverflowError):
            self.assertFieldToStreamEqual(None, -1000, IntegerField(1, 'little'))

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
