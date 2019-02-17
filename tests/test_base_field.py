import enum
import unittest

from destructify import Structure, BitField, FixedLengthField, DefinitionError, BaseFieldMixin, Field, EnumField, \
    IntegerField, ByteField, ConditionalField


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
