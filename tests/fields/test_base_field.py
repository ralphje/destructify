import enum
import unittest

from destructify import Structure, BitField, FixedLengthField, DefinitionError, BaseFieldMixin, Field, EnumField, \
    IntegerField, ByteField, ConditionalField, ArrayField, SwitchField
from tests import DestructifyTestCase


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
        self.assertEqual("struct.thing", Struct._meta.fields[0].base_field.full_name)
        self.assertIs(Struct._meta.fields[0].bound_structure, Struct._meta.fields[0].base_field.bound_structure)


class ConditionalFieldTest(unittest.TestCase):
    def test_depending_on_other_field(self):
        class ConditionalStructure(Structure):
            condition = ByteField()
            value = ConditionalField(IntegerField(2, 'big'), condition='condition')

        cs = ConditionalStructure.from_bytes(b"\0")
        self.assertEqual(0, cs.condition)
        self.assertIsNone(cs.value)
        self.assertEqual(b"\0", bytes(cs))

        cs = ConditionalStructure.from_bytes(b"\x01\0\x01")
        self.assertEqual(1, cs.condition)
        self.assertEqual(1, cs.value)
        self.assertEqual(b"\x01\0\x01", bytes(cs))


class ArrayFieldTest(DestructifyTestCase):
    def test_count(self):
        self.assertFieldStreamEqual(b"\x02\x01\x00\x01", [513, 1], ArrayField(IntegerField(2, 'big'), count=2))

    def test_length(self):
        self.assertFieldStreamEqual(b"\x02\x01\x00\x01", [513, 1], ArrayField(IntegerField(2, 'big'), length=4))
        self.assertFieldStreamEqual(b"\x02\x01\x00\x01", [b"\x02\x01\x00\x01"], ArrayField(FixedLengthField(-1), length=4))
        self.assertFieldStreamEqual(b"\x02\x01\x00\x01", [b"\x02\x01", b"\x00\x01"], ArrayField(FixedLengthField(2), length=4))
        self.assertFieldStreamEqual(b"\x02\x01\x00\x01", [b"\x02\x01", b"\x00\x01"], ArrayField(FixedLengthField(2), length=-1))

    def test_count_from_other_field(self):
        class SubStructure(Structure):
            length = IntegerField(1, signed=False)
            numbers = ArrayField(FixedLengthField(length=lambda s: s.length), count='length')

        s = SubStructure.from_bytes(b"\x02\x01\x02\x01\x02")
        self.assertEqual([b'\x01\x02', b'\x01\x02'], s.numbers)
        self.assertEqual(b"\x02\x01\x02\x01\x02", bytes(SubStructure(length=2, numbers=[b'\x01\x02', b'\x01\x02'])))
        s = SubStructure.from_bytes(b"\x01\x01")
        self.assertEqual([b'\x01'], s.numbers)
        self.assertEqual(b"\x01\x01", bytes(SubStructure(length=1, numbers=[b'\x01'])))

    def test_len(self):
        self.assertEqual(50, len(ArrayField(IntegerField(2, 'big'), count=25)))


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
        self.assertEqual(b'b', Struct(byte1=b'b').to_bytes())

    def test_flags(self):
        class Flags(enum.IntFlag):
            R = 4
            W = 2
            X = 1

        class EnumStructure(Structure):
            flag = EnumField(IntegerField(1), enum=Flags)

        self.assertEqual(Flags(0), EnumStructure.from_bytes(b"\0").flag)
        self.assertEqual(Flags.R | Flags.X, EnumStructure.from_bytes(b"\x05").flag)
        self.assertEqual(b"\x07", bytes(EnumStructure(flag=Flags.X | Flags.R | Flags.W)))


class SwitchFieldTest(DestructifyTestCase):
    def test_basic_switch(self):
        self.assertFieldStreamEqual(b"\x01", 1,
                                    SwitchField(cases={1: IntegerField(1), 2: IntegerField(2, 'little')}, switch=1))
        self.assertFieldStreamEqual(b"\x01\x01", 0x0101,
                                    SwitchField(cases={1: IntegerField(1), 2: IntegerField(2, 'little')}, switch=2))
        self.assertFieldStreamEqual(b"\x01", 1,
                                    SwitchField(cases={1: IntegerField(1), 2: IntegerField(2, 'little')}, switch='c'),
                                    parsed_fields={'c': 1})

    def test_switch_other(self):
        self.assertFieldStreamEqual(b"\x01", 1, SwitchField(cases={}, other=IntegerField(1), switch=1))
