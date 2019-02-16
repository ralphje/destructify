import io
import unittest

from destructify import Substream


class SubstreamTest(unittest.TestCase):
    def test_substream_with_negative_size(self):
        with self.assertRaises(ValueError):
            Substream(io.BytesIO(b"0123456789"), 7, 3)

    def test_substream_with_zero_size(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 3)
        self.assertEqual(b"", s.read())

    def test_boundaries_with_unbounded_read(self):
        s = Substream(io.BytesIO(b"0123456789"), 3, 6)
        self.assertEqual(b"345", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 3, 9)
        self.assertEqual(b"345678", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 8, 9)
        self.assertEqual(b"8", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 0, 9)
        self.assertEqual(b"012345678", s.read())
        s = Substream(io.BytesIO(b"0123456789"), 0, None)
        self.assertEqual(b"0123456789", s.read())
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
