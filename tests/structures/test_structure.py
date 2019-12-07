import io
from unittest import mock

import lazy_object_proxy

from destructify import ParsingContext, Structure, FixedLengthField, StringField, TerminatedField, IntegerField, \
    Substream, CheckError, WriteError, ImpossibleToCalculateLengthError, Field
from tests import DestructifyTestCase


class StructureDefaultTest(DestructifyTestCase):
    def test_default_from_other_field(self):
        class TestStructure(Structure):
            field0 = StringField(length=5)
            field1 = StringField(length=5, default=lambda c: c.field0)

        self.assertEqual(b"abcde", TestStructure(field0=b'abcde').field1)


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

        self.assertEqual(None, context.fields['field1'].raw)

    def test_context_set_from_stream(self):
        class TestStructure(Structure):
            field0 = StringField(length=5)

        self.assertIsInstance(TestStructure.from_bytes(b"asdfa")._context, ParsingContext)


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


class LengthTest(DestructifyTestCase):
    def test_length_empty_structure(self):
        class TestStructure(Structure):
            pass

        self.assertEqual(0, len(TestStructure))

    def test_length_sum_is_called(self):
        class TestStructure(Structure):
            x = Field()
            y = Field()

        # Note: we patch the return value of the length, so it does not matter what we specify above
        with mock.patch.object(TestStructure._meta.fields[0], '_length_sum', side_effect=lambda x: 1) as mock_method, \
            mock.patch.object(TestStructure._meta.fields[1], '_length_sum', side_effect=lambda x: 3) as mock_method2:
            len(TestStructure)

        mock_method.assert_called_once_with(0)
        mock_method2.assert_called_once_with(1)

    def test_length_sum_exception_when_impossible_to_calculate(self):
        class TestStructure(Structure):
            x = Field()
            y = Field()

        # Note: we patch the return value of the length, so it does not matter what we specify above
        with mock.patch.object(TestStructure._meta.fields[0], '_length_sum', side_effect=ImpossibleToCalculateLengthError):
            with self.assertRaises(ImpossibleToCalculateLengthError):
                len(TestStructure)

    def test_length_option_in_len_function(self):
        class TestStructure(Structure):
            class Meta:
                length = 3

        self.assertEqual(3, len(TestStructure))

        class TestStructure2(Structure):
            a = FixedLengthField(length=5)

            class Meta:
                length = 3

        self.assertEqual(3, len(TestStructure2))

    def test_length_option_in_unbounded_field(self):
        class TestStructure(Structure):
            a = FixedLengthField(length=-1)

            class Meta:
                length = 3

        self.assertEqual(TestStructure(a=b"a"), TestStructure.from_bytes(b"a"))
        self.assertEqual(TestStructure(a=b"aaa"), TestStructure.from_bytes(b"aaaaaaaaaaaa"))

        with self.assertRaises(WriteError):
            TestStructure(a=b"aaaaaaaaaa").to_bytes()
        self.assertEqual(b"aaa", TestStructure(a=b"aaa").to_bytes())
        self.assertEqual(b"a", TestStructure(a=b"a").to_bytes())


class InitializeFinalizeTest(DestructifyTestCase):
    def test_initializer_called(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)

        context = ParsingContext()
        with mock.patch.object(TestStructure, 'initialize', side_effect=lambda x: x) as mock_method:
            TestStructure.from_stream(io.BytesIO(b"123"), context)
        mock_method.assert_called_once_with(context)

    def test_finalizer_called(self):
        class TestStructure(Structure):
            field1 = FixedLengthField(length=3)

        context = ParsingContext()
        with mock.patch.object(TestStructure, 'finalize', side_effect=lambda x: x) as mock_method:
            TestStructure(field1=b'asd').to_stream(io.BytesIO(), context)
        mock_method.assert_called_once_with(context)


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

    def test_lazy_decoded(self):
        class TestStructure(Structure):
            field1 = IntegerField(length=1, decoder=lambda x: x+10, lazy=True)

        t = TestStructure.from_bytes(b"\x01")
        self.assertIsInstance(t.field1, lazy_object_proxy.Proxy)
        self.assertEqual(11, int(t.field1))


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

