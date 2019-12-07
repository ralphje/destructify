import io
import unittest

from destructify import Substream, CaptureStream


class TellableStream:
    def __init__(self, raw):
        self.raw = raw

    def __getattr__(self, item):
        return getattr(self.raw, item)

    def seekable(self):
        return False

    def seek(self, a, b=0):
        raise io.UnsupportedOperation()


class UnseekableStream(TellableStream):
    def tell(self):
        raise io.UnsupportedOperation()


class SubstreamTest(unittest.TestCase):
    def test_negative_size(self):
        with self.assertRaises(ValueError):
            Substream(io.BytesIO(b"0123456789"), start=7, stop=3)
        with self.assertRaises(ValueError):
            Substream(io.BytesIO(b"0123456789"), start=0, length=-3)

    def test_stop_and_length(self):
        with self.assertRaises(ValueError):
            Substream(io.BytesIO(b"0123456789"), start=0, stop=2, length=2)

    def test_start_none(self):
        for wrapper in (lambda f: f, TellableStream):
            with self.subTest(wrapper=wrapper):
                b = io.BytesIO(b"0123456789")
                b.seek(2)
                s = TellableStream(Substream(wrapper(b), start=None))
                self.assertEqual(2, s.start)
                self.assertEqual(b"23", s.read(2))

        with self.subTest(wrapper=UnseekableStream):
            b = io.BytesIO(b"0123456789")
            b.seek(2)
            s = TellableStream(Substream(UnseekableStream(b), start=None))
            self.assertEqual(0, s.start)
            self.assertEqual(b"23", s.read(2))

    def test_start_unseekable(self):
        with self.subTest(wrapper=TellableStream):
            with self.assertRaises(OSError):
                Substream(TellableStream(io.BytesIO(b"0123456789")), 3, 6)
        with self.subTest(wrapper=UnseekableStream):
            s = Substream(UnseekableStream(io.BytesIO(b"0123456789")), 3, 6)
            self.assertEqual(3, s.start)
            self.assertEqual(0, s.tell())

    def test_substream_with_zero_size(self):
        for wrapper in (lambda f: f, TellableStream, UnseekableStream):
            with self.subTest(wrapper=wrapper):
                s = Substream(wrapper(io.BytesIO(b"0123456789")), start=0, stop=0)
                self.assertEqual(b"", s.read())

    def test_boundaries_with_unbounded_read(self):
        for wrapper in (lambda f: f, TellableStream, UnseekableStream):
            with self.subTest(wrapper=wrapper):
                s = Substream(wrapper(io.BytesIO(b"0123456789")), 0, 9)
                self.assertEqual(b"012345678", s.read())
                s = Substream(wrapper(io.BytesIO(b"0123456789")), 0, None)
                self.assertEqual(b"0123456789", s.read())

    def test_boundaries_with_unbounded_read_other_start(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 6)
        self.assertEqual(b"345", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 3, 9)
        self.assertEqual(b"345678", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 8, 9)
        self.assertEqual(b"8", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 7, None)
        self.assertEqual(b"789", s.read())

    def test_tell_and_seek_set(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 6)

        self.assertEqual(0, s.tell())
        self.assertEqual(1, s.seek(1))
        self.assertEqual(b"4", s.read(1))
        self.assertEqual(2, s.tell())
        self.assertEqual(b"5", s.read(2))
        self.assertEqual(b"", s.read(2))

    def test_tell_and_seek_set_unseekable(self):
        s = Substream(UnseekableStream(io.BytesIO(b"012")), 3, 6)

        self.assertEqual(0, s.tell())
        with self.assertRaises(OSError):
            self.assertEqual(1, s.seek(1))
        self.assertEqual(b"0", s.read(1))
        self.assertEqual(1, s.tell())
        self.assertEqual(b"12", s.read(2))
        self.assertEqual(b"", s.read(2))

    def test_tell_and_seek_from_cur(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 6)

        self.assertEqual(0, s.tell())
        self.assertEqual(b"34", s.read(2))
        self.assertEqual(1, s.seek(-1, io.SEEK_CUR))
        self.assertEqual(1, s.tell())
        self.assertEqual(b"45", s.read(2))

    def test_tell_and_seek_from_end(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 6)

        self.assertEqual(0, s.tell())
        self.assertEqual(2, s.seek(-1, io.SEEK_END))
        self.assertEqual(2, s.tell())
        self.assertEqual(b"5", s.read(2))

    def test_tell_and_seek_from_end_unbounded_substream(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, None)

        self.assertEqual(0, s.tell())
        self.assertEqual(5, s.seek(-2, io.SEEK_END))
        self.assertEqual(5, s.tell())
        self.assertEqual(b"89", s.read(2))

    def test_stream_after_closing_is_at_correct_position(self):
        stream = io.BytesIO(b"0123456789")

        with Substream(stream, 3, None) as s:
            self.assertEqual(0, s.tell())
            self.assertEqual(b"34", s.read(2))

        self.assertEqual(3+2, stream.tell())

    def test_stream_that_is_closed_twice_is_at_correct_position(self):
        # This can occur sometimes. Using a huge stream of bytes to attempt to trigger a
        # successful seek twice.
        stream = io.BytesIO(b"0123456789"*10000)

        with Substream(stream, 8000) as s:
            self.assertEqual(0, s.tell())
            self.assertEqual(b"0123456789"*28, s.read(280))
            s.close()

        self.assertEqual(8280, stream.tell())

    def test_attribute_that_is_not_present_in_raw(self):
        stream = io.BytesIO(b"")
        self.assertEqual(False, hasattr(stream, 'peek'))
        stream.peek = lambda: None
        self.assertEqual(True, hasattr(stream, 'peek'))


class CaptureStreamTest(unittest.TestCase):
    def test_readable(self):
        cs = CaptureStream(io.BytesIO(b"asdfasdfasddf"))
        cs.seek(5)
        self.assertEqual(b"sdfasddf", cs.read(8))
        self.assertEqual(b"sdfasddf", cs.cache_read_last(8))
        self.assertEqual(b"sdfasddf", cs.cache_read_last(8))

    def test_read_unseekable(self):
        cs = CaptureStream(UnseekableStream(io.BytesIO(b"asdfasdfasddf")))
        self.assertEqual(b"asdf", cs.read(4))
        self.assertEqual(b"asdf", cs.cache_read_last(4))
        self.assertEqual(b"asdf", cs.cache_read_last(4))

    def test_write(self):
        cs = CaptureStream(io.BytesIO(b"asdfasdfasddf"))
        cs.seek(5)
        cs.write(b"borp")
        self.assertEqual(b"borp", cs.cache_read_last(4))
        self.assertEqual(b"borp", cs.cache_read_last(4))
