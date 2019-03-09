import io
from unittest import mock

from destructify import ParsingContext, Structure, FixedLengthField, StringField
from tests import DestructifyTestCase


class StructureParsingTest(DestructifyTestCase):
    def test_raw_bytes_are_read(self):
        context = ParsingContext(capture_raw=True)
        class TestStructure(Structure):
            field1 = StringField(length=5)

        TestStructure.from_stream(io.BytesIO(b"abcdef"), context)

        self.assertEqual(b"abcde", context.fields['field1'].raw)

    def test_raw_bytes_are_not_read_if_capture_is_false(self):
        context = ParsingContext(capture_raw=False)
        class TestStructure(Structure):
            field1 = StringField(length=5)

        TestStructure.from_stream(io.BytesIO(b"abcdef"), context)

        self.assertEqual(False, hasattr(context.fields['field1'], 'raw'))


class InitializeFinalizeTest(DestructifyTestCase):
    def test_initializer_called(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)

        with mock.patch.object(TestStructure, 'initialize', side_effect=lambda x: x) as mock_method:
            TestStructure.from_bytes(b"123")
        mock_method.assert_called_once_with({"field1": b"123"})

    def test_finalizer_called(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)

        with mock.patch.object(TestStructure, 'finalize', side_effect=lambda x: x) as mock_method:
            TestStructure(field1=b'asd').to_bytes()
        mock_method.assert_called_once_with({"field1": b"asd"})


class OffsetTest(DestructifyTestCase):
    def test_absolute_offset(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3, offset=2)

        self.assertStructureStreamEqual(b"\0\0cde", TestStructure(field1=b"cde"))

    def test_two_absolute_offsets(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3, offset=2)
            field2 = FixedLengthField(length=2, offset=0)

        self.assertStructureStreamEqual(b"abcde", TestStructure(field1=b"cde", field2=b"ab"))

    def test_absolute_offset_followed_by_relative(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3, offset=2)
            field2 = FixedLengthField(length=2)

        self.assertStructureStreamEqual(b"\0\0cdefg", TestStructure(field1=b"cde", field2=b"fg"))

    # TODO: negative offset writing

    def test_negative_offset(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)
            field2 = FixedLengthField(length=2, offset=-3)

        self.assertEqual(TestStructure(field1=b"abc", field2=b"de"), TestStructure.from_bytes(b"abcXXXXXdef"))

    def test_relative_offset(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)
            field2 = FixedLengthField(length=2, skip=2)

        self.assertStructureStreamEqual(b"abc\0\0fg", TestStructure(field1=b"abc", field2=b"fg"))

