import enum
import unittest

from destructify import Structure, BitField, FixedLengthField, DefinitionError, BaseFieldMixin, Field, EnumField


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

