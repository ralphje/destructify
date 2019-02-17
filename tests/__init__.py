import io
import unittest

from destructify import ParsingContext


class DestructifyTestCase(unittest.TestCase):
    def call_field_to_stream(self, field, value):
        stream = io.BytesIO()
        field.to_stream(stream, value, ParsingContext())
        return stream.getvalue()

    def assertFieldToStreamEqual(self, expected, field, value):
        self.assertEqual(expected, self.call_field_to_stream(field, value))

    def call_field_from_stream(self, field, value):
        return field.from_stream(io.BytesIO(value), ParsingContext())

    def assertFieldFromStreamEqual(self, expected_result, field, value, expected_read=None):
        res = self.call_field_from_stream(field, value)
        self.assertEqual(expected_result, res[0])
        if expected_read is not None:
            self.assertEqual(expected_read, res[1])

    def assertFieldStreamEqual(self, expected_bytes, expected_python, field):
        self.assertFieldToStreamEqual(expected_bytes, field, expected_python)
        self.assertFieldFromStreamEqual(expected_python, field, expected_bytes)

    def assertStructureStreamEqual(self, expected_bytes, expected_structure):
        self.assertEqual(expected_structure, expected_structure.__class__.from_bytes(expected_bytes))
        self.assertEqual(expected_bytes, bytes(expected_structure))
