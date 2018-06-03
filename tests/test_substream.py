import io
import unittest

from destructify import Substream


class SubstreamTest(unittest.TestCase):
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
