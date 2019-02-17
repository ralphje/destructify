import unittest
import destructify


class ReadmeExampleTest(unittest.TestCase):
    def test_readme_example(self):
        class ExampleStructure(destructify.Structure):
            some_number = destructify.IntegerField(default=0x13, length=4, byte_order='little', signed=True)
            length = destructify.IntegerField(length=1)
            data = destructify.FixedLengthField(length='length')

        example = ExampleStructure.from_bytes(b"\x01\x02\x03\x04\x0BHello world")
        self.assertEqual(b"Hello world", example.data)

        example2 = ExampleStructure(data=b'How are you doing?')
        self.assertEqual(b'\x13\x00\x00\x00\x12How are you doing?', bytes(example2))
