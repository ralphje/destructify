import io

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
