import io
import unittest

from destructify import ParsingContext


class DestructifyTestCase(unittest.TestCase):
    def call_field_to_stream(self, field, value, *, parsed_fields=None):
        stream = io.BytesIO()
        field.to_stream(stream, value, ParsingContext(parsed_fields=parsed_fields))
        return stream.getvalue()

    def call_field_from_stream(self, field, value, *, parsed_fields=None):
        return field.from_stream(io.BytesIO(value), ParsingContext(parsed_fields=parsed_fields))

    def assertFieldToStreamEqual(self, expected_bytes, python, field, *, parsed_fields=None):
        self.assertEqual(expected_bytes, self.call_field_to_stream(field, python, parsed_fields=parsed_fields))

    def assertFieldFromStreamEqual(self, bytes, expected_python, field, *, expected_read=None, parsed_fields=None):
        res = self.call_field_from_stream(field, bytes, parsed_fields=parsed_fields)
        self.assertEqual(expected_python, res[0])
        if expected_read is not None:
            self.assertEqual(expected_read, res[1])

    def assertFieldStreamEqual(self, expected_bytes, expected_python, field, *, parsed_fields=None):
        self.assertFieldToStreamEqual(expected_bytes, expected_python, field, parsed_fields=parsed_fields)
        self.assertFieldFromStreamEqual(expected_bytes, expected_python, field, parsed_fields=parsed_fields)

    def assertStructureStreamEqual(self, expected_bytes, expected_structure):
        self.assertEqual(expected_structure, expected_structure.__class__.from_bytes(expected_bytes))
        self.assertEqual(expected_bytes, bytes(expected_structure))
