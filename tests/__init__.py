import io
import unittest

from destructify import ParsingContext


class DestructifyTestCase(unittest.TestCase):
    def call_to_stream(self, field, value):
        stream = io.BytesIO()
        field.to_stream(stream, value, ParsingContext())
        return stream.getvalue()

    def assertToStreamEqual(self, expected, field, value):
        self.assertEqual(expected, self.call_to_stream(field, value))

    def call_from_stream(self, field, value):
        return field.from_stream(io.BytesIO(value), ParsingContext())

    def assertFromStreamEqual(self, expected_result, field, value, expected_read=None):
        res = self.call_from_stream(field, value)
        self.assertEqual(expected_result, res[0])
        if expected_read is not None:
            self.assertEqual(expected_read, res[1])
