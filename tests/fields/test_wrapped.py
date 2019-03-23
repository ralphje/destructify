import enum
import unittest

from destructify import Structure, BitField, FixedLengthField, DefinitionError, WrappedFieldMixin, Field, EnumField, \
    IntegerField, ByteField, ConditionalField, ArrayField, SwitchField, ConstantField, WrongMagicError, WriteError, \
    ParseError, io, ParsingContext
from tests import DestructifyTestCase


class BaseFieldTestCase(unittest.TestCase):
    def test_wrong_initialization(self):
        class MyField(WrappedFieldMixin, Field):
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
        class MyField(WrappedFieldMixin, Field):
            pass

        class Struct(Structure):
            thing = MyField(BitField(1))

        self.assertEqual("thing", Struct._meta.fields[0].base_field.name)
        self.assertEqual("Struct.thing", Struct._meta.fields[0].base_field.full_name)
        self.assertIs(Struct._meta.fields[0].bound_structure, Struct._meta.fields[0].base_field.bound_structure)


class ConstantFieldTest(DestructifyTestCase):
    def test_simple(self):
        self.assertFieldStreamEqual(b"hello", b"hello", ConstantField(b"hello"))

    def test_wrong_read(self):
        with self.assertRaises(WrongMagicError):
            self.call_field_from_stream(ConstantField(b"hello"), b"derp2")

    def test_wrong_write(self):
        with self.assertRaises(WriteError):
            self.call_field_to_stream(ConstantField(b"hello"), b"derp2")

    def test_default_is_set(self):
        self.assertEqual(True, ConstantField(b"hello").has_default)
        self.assertEqual(b"hello", ConstantField(b"hello").default)

        self.assertEqual(True, ConstantField(b"hello", default=12).has_default)
        self.assertEqual(12, ConstantField(b"hello", default=12).default)

    def test_based_on_other_field(self):
        self.assertFieldStreamEqual(b"\xf1", 0xf1, ConstantField(0xf1, base_field=IntegerField(length=1)))
        with self.assertRaises(WrongMagicError):
            self.call_field_from_stream(ConstantField(0xf1, base_field=IntegerField(length=1)), b"\xf2")
        with self.assertRaises(WriteError):
            self.call_field_to_stream(ConstantField(0xf1, base_field=IntegerField(length=1)), 12)

    def test_wrong_constant_value(self):
        with self.assertRaises(DefinitionError):
            ConstantField(0xf1)

    def test_override_on_inner_field(self):
        self.assertEqual(3, ConstantField(0xf1, base_field=IntegerField(length=1, override=3)).override)
        self.assertEqual(3, ConstantField(0xf1, base_field=IntegerField(length=1), override=3).override)

    def test_encode_on_inner_field(self):
        self.assertFieldStreamEqual(
            b'\x24', 0x12,
            ConstantField(0x12, base_field=IntegerField(length=1, encoder=lambda x: x+0x12, decoder=lambda x: x-0x12))
         )


class ConditionalFieldTest(DestructifyTestCase):
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

    def test_conditional_with_constant_full(self):
        class ConditionalStructure(Structure):
            condition = ByteField()
            value = ConditionalField(ConstantField(1, IntegerField(1)), condition='condition')

        self.assertStructureStreamEqual(b'\x01\x01', ConditionalStructure(condition=True, value=1))
        self.assertStructureStreamEqual(b'\x00', ConditionalStructure(condition=False, value=None))
        # test whether default is set properly
        self.assertEqual(b"\x01\x01", ConditionalStructure(condition=True).to_bytes())
        self.assertEqual(b"\x00", ConditionalStructure(condition=False).to_bytes())

    def test_conditional_field_encoder(self):
        self.assertFieldStreamEqual(b'\x11', 0x01,
                                    ConditionalField(IntegerField(1, encoder=lambda x: x+0x10, decoder=lambda x: x-0x10),
                                                     condition=True))


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

    def test_count_from_other_field_override(self):
        class TestStruct(Structure):
            length = IntegerField(1, signed=False)
            numbers = ArrayField(IntegerField(length=1), count='length')

        self.assertEqual(b'\x02\x01\x03', bytes(TestStruct(numbers=[1, 3])))
        # sanity check
        self.assertStructureStreamEqual(b'\x02\x01\x03', TestStruct(length=2, numbers=[1, 3]))

    def test_context(self):
        class TestStruct(Structure):
            numbers = ArrayField(IntegerField(length=1), count=3)

        context = ParsingContext()
        TestStruct.from_stream(io.BytesIO(b'\x02\x01\x03'), context)

        self.assertIsInstance(context.fields['numbers'].subcontext, ParsingContext)
        self.assertEqual(2, context.fields['numbers'].subcontext.fields[0].value)
        self.assertEqual(1, context.fields['numbers'].subcontext.fields[1].value)
        self.assertEqual(3, context.fields['numbers'].subcontext.fields[2].value)

    def test_len(self):
        self.assertEqual(50, len(ArrayField(IntegerField(2, 'big'), count=25)))


class EnumFieldTest(DestructifyTestCase):
    def test_len(self):
        self.assertEqual(1, len(EnumField(FixedLengthField(1), enum.Enum)))

    def test_parsing(self):
        class En(enum.Enum):
            TEST = b'b'

        class Struct(Structure):
            byte1 = EnumField(FixedLengthField(1), En)

        s = Struct.from_bytes(b"b")
        self.assertEqual(En.TEST, s.byte1)

        with self.assertRaises(ParseError):
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

    def test_default_from_inner(self):
        class Flags(enum.IntFlag):
            R = 4
            W = 2
            X = 1

        class EnumStructure(Structure):
            flag = EnumField(IntegerField(1, default=Flags.X), enum=Flags)

        self.assertEqual(b"\x01", bytes(EnumStructure()))

    def test_obtain_value(self):
        class En(enum.Enum):
            TEST = b'b'
        field = EnumField(FixedLengthField(1), En)

        self.assertFieldToStreamEqual(b'b', En.TEST, field)
        self.assertFieldToStreamEqual(b'b', 'TEST', field)
        self.assertFieldToStreamEqual(b'b', b'b', field)
        with self.assertRaises(TypeError):
            self.assertFieldToStreamEqual(b'b', 'x', field)
