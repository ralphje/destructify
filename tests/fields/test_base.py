import unittest

from destructify import Structure, IntField, StructField, DefinitionError, Field, FixedLengthField, IntegerField
from tests import DestructifyTestCase


class FieldTest(DestructifyTestCase):
    def test_initialize_offset_skip(self):
        self.assertEqual(3, Field(offset=3).offset)
        with self.assertRaises(DefinitionError):
            Field(offset=3, skip=3)
        with self.assertRaises(DefinitionError):
            Field(skip=-3)

    def test_aligned_field(self):
        def align(a):
            class Struct(Structure):
                f1 = FixedLengthField(2)
                f2 = FixedLengthField(1)
                f3 = FixedLengthField(3)

                class Meta:
                    alignment = a
            return Struct

        self.assertStructureStreamEqual(b"12\0\0a\0\0\0bbb", align(4)(f1=b'12', f2=b'a', f3=b'bbb'))
        self.assertStructureStreamEqual(b"12abbb", align(1)(f1=b'12', f2=b'a', f3=b'bbb'))
        self.assertStructureStreamEqual(b"12a\0bbb", align(2)(f1=b'12', f2=b'a', f3=b'bbb'))

    def test_aligned_field_with_skip(self):
        def align(a):
            class Struct(Structure):
                f1 = FixedLengthField(2)
                f2 = FixedLengthField(1, skip=0)
                f3 = FixedLengthField(3)

                class Meta:
                    alignment = a
            return Struct

        self.assertStructureStreamEqual(b"12a\0bbb", align(4)(f1=b'12', f2=b'a', f3=b'bbb'))

    def test_encoder_decoder(self):
        class Struct(Structure):
            field = IntegerField(1, encoder=lambda v: v + 1, decoder=lambda v: v - 1)

        self.assertStructureStreamEqual(b"\x02", Struct(field=1))

    def test_encoder_and_override(self):
        class Struct(Structure):
            field = IntegerField(1, encoder=lambda v: v + 1, override=lambda c, v: v + 1)

        self.assertEqual(b"\x03", Struct(field=1).to_bytes())

    def test_with_name(self):
        f = Field(name="blah")
        self.assertEqual("blah", f.name)
        with f.with_name(name="foo") as field_instance:
            self.assertEqual("foo", field_instance.name)
        self.assertEqual("blah", f.name)
        with f.with_name(name=None) as field_instance:
            self.assertEqual("blah", field_instance.name)
        self.assertEqual("blah", f.name)
