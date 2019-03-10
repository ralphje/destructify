import io
from unittest import mock

import lazy_object_proxy

from destructify import ParsingContext, Structure, FixedLengthField, StringField, TerminatedField, IntegerField, \
    Substream, CheckError
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


class ChecksTest(DestructifyTestCase):
    def test_checks_work(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=5)
            field2 = FixedLengthField(length=5)

            class Meta:
                checks = [
                    lambda c: c.field1 == c.field2
                ]

        with self.assertRaises(CheckError):
            TestStructure.from_bytes(b"abcde12345")
        TestStructure.from_bytes(b"abcdeabcde")


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


class LazyTest(DestructifyTestCase):
    def test_lazy_field(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3, lazy=True)

        t = TestStructure.from_bytes(b"123")
        self.assertIsInstance(t.field1, lazy_object_proxy.Proxy)
        self.assertEqual(b"123", bytes(t.field1))

    def test_lazy_field_that_cannot_be_lazy(self):
        class TestStructure(Structure):
            field1 = TerminatedField(b'\0', lazy=True)
            field2 = FixedLengthField(length=3)

        t = TestStructure.from_bytes(b"123\x00123")
        self.assertNotIsInstance(t.field1, lazy_object_proxy.Proxy)
        self.assertEqual(b"123", bytes(t.field1))

    def test_lazy_field_at_the_end(self):
        class TestStructure(Structure):
            field1 = TerminatedField(b'\0', lazy=True)
            field2 = FixedLengthField(length=3, lazy=True)
            field3 = TerminatedField(b'\0', lazy=True)

        t = TestStructure.from_bytes(b"123\x00123123\0")
        self.assertNotIsInstance(t.field1, lazy_object_proxy.Proxy)
        self.assertIsInstance(t.field2, lazy_object_proxy.Proxy)
        self.assertIsInstance(t.field3, lazy_object_proxy.Proxy)

        self.assertEqual(b"123", bytes(t.field1))
        self.assertEqual(b"123", bytes(t.field2))
        self.assertEqual(b"123", bytes(t.field3))

    def test_write_lazy(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3, lazy=True)

        t = TestStructure.from_bytes(b"123\x00123123\0")
        self.assertIsInstance(t.field1, lazy_object_proxy.Proxy)

        self.assertEqual(b"123", t.to_bytes())

    def test_depend_on_lazy(self):
        class TestStructure(Structure):
            field1 = IntegerField(length=1, lazy=True)
            field2 = FixedLengthField(length='field1', lazy=True)
            field3 = FixedLengthField(length=1)

        t = TestStructure.from_bytes(b"\x031231")
        self.assertNotIsInstance(t.field1, lazy_object_proxy.Proxy)  # should be resolved now
        self.assertIsInstance(t.field2, lazy_object_proxy.Proxy)

    def test_depend_on_lazy_later_defined_field(self):
        class TestStructure(Structure):
            field2 = FixedLengthField(length='length', lazy=True)
            field3 = FixedLengthField(length=1)
            length = IntegerField(offset=4, length=1, lazy=True)

        t = TestStructure.from_bytes(b"1231\x03")
        self.assertIsInstance(t.field2, lazy_object_proxy.Proxy)
        self.assertNotIsInstance(t.length, lazy_object_proxy.Proxy)  # should be resolved now

    def test_offset_lazy_needs_no_resolving(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=1, lazy=True)
            field2 = IntegerField(offset=1, length=1, lazy=True)

        t = TestStructure.from_bytes(b"12")
        self.assertIsInstance(t.field1, lazy_object_proxy.Proxy)
        self.assertIsInstance(t.field2, lazy_object_proxy.Proxy)

    def test_lazy_negative_offset_field(self):
        class TestStructure(Structure):
            field2 = FixedLengthField(length='length', lazy=True)
            field3 = FixedLengthField(length=1)
            length = IntegerField(offset=-1, length=1, lazy=True)

        t = TestStructure.from_bytes(b"1231\x03")
        self.assertIsInstance(t.field2, lazy_object_proxy.Proxy)
        self.assertNotIsInstance(t.length, lazy_object_proxy.Proxy)  # should be resolved now


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

