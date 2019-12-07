import functools
import io

from ..exceptions import MisalignedFieldError, StreamExhaustedError


class _PurePythonIOImplementationMixin:
    """Provides a base implementation for several functions that all can be implemented by another function.

    Requires self.raw to be set.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration()
        return line

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def __getattribute__(self, item):
        if item in ('read', 'read1', 'readall', 'readinto', 'readinto1', 'readline', 'readlines', 'write', 'writelines') and \
                not hasattr(self.raw, item):
            raise AttributeError()
        return super().__getattribute__(item)

    def detach(self):
        return self.raw

    def _read(self, size, func):
        return func(size)

    def read(self, size=-1):
        return self._read(size, self.raw.read)

    def read1(self, size):
        return self._read(size, self.raw.read1)

    def readall(self):
        res = bytearray()
        while True:
            data = self.read(io.DEFAULT_BUFFER_SIZE)
            if not data:
                break
            res += data
        if res:
            return bytes(res)
        else:
            return data

    def _readinto(self, b, func):
        if not isinstance(b, memoryview):
            b = memoryview(b)
        b = b.cast('B')

        data = func(len(b))
        n = len(data)
        b[:n] = data
        return n

    def readinto(self, b):
        return self._readinto(b, self.read)

    def readinto1(self, b):
        return self._readinto(b, self.read1)

    def readline(self, size=-1):
        return self._read(size, self.raw.readline)

    def readlines(self, hint=-1):
        if hint is None or hint <= 0:
            return list(self)
        n = 0
        lines = []
        for line in self:
            lines.append(line)
            n += len(line)
            if n >= hint:
                break
        return lines

    def write(self, b):
        return self.raw.write(b)

    def writelines(self, lines):
        for line in lines:
            self.write(line)


class CaptureStream(_PurePythonIOImplementationMixin):
    """Represents a view of a stream, but ensures that the internal pointer goes never beyond its provided boundaries.
    """

    def __init__(self, raw):
        """
        :param raw: The raw underlying stream.
        """

        self.raw = raw
        self.cache_reset()

    def cache_read_last(self, count):
        self._cache.seek(-count, io.SEEK_CUR)
        return self._cache.read(count)

    def cache_reset(self):
        self._cache = io.BytesIO()
        self._cache_offset = 0
        try:
            self._cache_offset = self.raw.tell()
        except (AttributeError, OSError):  # raised when this is not a tellable stream
            pass
        # TODO: This is highly inefficient use of BytesIO, we should not cache all NULL bytes before the seek.
        self._cache.seek(self._cache_offset)

    def __getattribute__(self, item):
        if item in ('peek', 'read', 'read1', 'readall', 'readinto', 'readinto1', 'readline', 'readlines', 'write') and \
                not hasattr(self.raw, item):
            raise AttributeError()
        return super().__getattribute__(item)

    def __getattr__(self, item):
        # All unimplemented methods go to the raw stream directly.
        return getattr(self.raw, item)

    def close(self):
        pass  # CaptureStream is not intended to be closed

    def detach(self):
        return self.raw

    def _read(self, size, func):
        result = func(size)
        self._cache.write(result)
        return result

    def seek(self, offset, whence=0):
        result = self.raw.seek(offset, whence)
        self._cache.seek(result)
        return result

    def write(self, b):
        result = self.raw.write(b)
        self._cache.write(b[:result])
        return result


class Substream(_PurePythonIOImplementationMixin):
    """Represents a view of a stream, but ensures that the internal pointer goes never beyond its provided boundaries.
    """

    def __init__(self, raw, start=None, stop=None, *, length=None):
        """

        :param raw: The raw underlying stream.
        :param start: The offset in the stream. If not provided, equals raw.tell().
        :param stop: The stop offset in the stream. Implies length = stop - start.
        :param length: The length of the stream.
        """

        if stop is not None and length is not None:
            raise ValueError("Can not initialize Substream with both a stop and a length.")
        if start is not None and stop is not None and start > stop:
            raise ValueError("Can not initialize Substream with a start larger than stop.")
        if start is not None and start < 0 or stop is not None and stop < 0 or length is not None and length < 0:
            raise ValueError("Can not initialize Substream with negative start, stop, or length.")

        self.raw = raw
        self.start = start
        self.length = length

        # obtain the current position
        try:
            if self.start is None:
                self.start = self.raw.tell()
                self._position = 0
            else:
                self._position = self.raw.tell() - self.start
        except (AttributeError, OSError):  # raised when this is not a tellable stream
            if self.start is None:
                self.start = 0
            self._position = 0
            self._tellable = False
        else:
            self._tellable = True

            # seek to the start of the substream, if the position is before the start of it
            # also seek to the current position to determine if we are a seekable stream
            # this makes no sense if we are not in a tellable stream
            try:
                self.raw.seek(self.start + max(0, self._position))
            except (AttributeError, OSError):
                if self._position != 0:
                    raise OSError("The stream is not at its starting position, and cannot seek to starting position.")
            self._position = max(0, self._position)

        # put stop in the place of length if we have defined it.
        # there's a check above to verify that not both stop and length are set.
        if stop is not None:
            self.length = stop - self.start

    def __getattribute__(self, item):
        if item in ('peek', 'write') and \
                not hasattr(self.raw, item):
            raise AttributeError()
        return super().__getattribute__(item)

    def __getattr__(self, item):
        # All unimplemented methods go to the raw stream directly.
        return getattr(self.raw, item)

    def _update_position(self):
        """Internal: called at the start of all functions that require our position to be correct."""
        self._update_position_from_raw()
        self._check_bounds()

    def _update_position_from_raw(self):
        if self._tellable:
            self._position = self.raw.tell() - self.start
            self._check_bounds()

    def _check_bounds(self):
        if self._position < 0:
            self._position = 0
            self.raw.seek(self.start + self._position)

        elif self.length is not None and self._position > self.length:
            self._position = self.length
            self.raw.seek(self.start + self._position)

    def _cap_amount_of_bytes(self, size):
        size = size.__index__()
        if self.length is None:
            # There is no upper bound, we can read anything
            return size
        else:
            # There is an upper bound in this stream
            max_to_read = self.length - self._position

            if size is None or size < 0:
                # There is no upper bound on reading, return the amount of bytes until we hit the size limit
                return max_to_read
            return min(max_to_read, size)

    def close(self):
        pass  # substream is not intended to be able to be closed

    def peek(self, size=-1):
        self._update_position()
        return self.raw.peek(self._cap_amount_of_bytes(size))

    def _read(self, size, func):
        self._update_position()
        result = func(self._cap_amount_of_bytes(size))
        self._position += len(result)
        return result

    def seek(self, offset, whence=0):
        if not self.seekable():
            raise io.UnsupportedOperation("Non-seekable stream")

        if whence == io.SEEK_SET:
            if offset < 0:
                raise ValueError("negative seek position {}".format(offset))
            self._position = offset

        elif whence == io.SEEK_CUR:
            self._update_position_from_raw()
            self._position = max(0, self._position + offset)

        elif whence == io.SEEK_END:
            if self.length is None:
                self.raw.seek(offset, io.SEEK_END)
                self._update_position_from_raw()  # can't know for sure we are not beyond start boundary
            else:
                self._position = max(0, self.length + offset)

        else:
            raise ValueError("unsupported whence value")

        self._check_bounds()
        self.raw.seek(self.start + self._position)
        return self._position

    def seekable(self):
        return self.raw.seekable()

    def tell(self):
        self._update_position()
        return self._position

    def truncate(self, size=None):
        if size is None:
            size = self.tell()
        self.length = min(self.length, size)
        return self.length

    def writable(self):
        return self.raw.writable()

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def write(self, b):
        self._update_position()
        length = self._cap_amount_of_bytes(len(b))
        if length < len(b):
            raise IOError("Attempting to write more bytes than allowed in substream; attempting to write "
                          "{}, only {} available.".format(len(b), length))

        result = self.raw.write(b[:length])
        self._position += result
        return result


class BitStream:
    """A object that acts as if it is a stream, but adds methods for reading bits"""

    def __init__(self, raw):
        """
        :param raw: The raw underlying stream.
        """

        self.raw = raw
        self._bits_remaining = None

    def __getattribute__(self, item):
        # Adjusts __getattribute__ to remove methods that are not in the underlying stream.
        if item in ('flush', 'peek', 'read', 'read1', 'readall', 'readinto', 'readinto1', 'readline', 'readlines',
                    'seek', 'write', 'writelines') \
                and not hasattr(self.raw, item):
            raise AttributeError(item)
        return super().__getattribute__(item)

    def __getattr__(self, item):
        # All unimplemented methods go to the raw stream directly.
        result = getattr(self.raw, item)

        # If the gotten function is one of these, we wrap it in a 'decorator' that verifies the field is aligned.
        if item in ('flush', 'peek', 'read', 'read1', 'readall', 'readinto', 'readinto1', 'readline', 'readlines',
                    'seek', 'write', 'writelines'):
            @functools.wraps(result)
            def wrapper(*args, **kwargs):
                self._check_aligned()
                return result(*args, **kwargs)

            return wrapper

        return result

    def _check_aligned(self):
        if self._bits_remaining:
            raise MisalignedFieldError("A field following a BitField is misaligned. %s bits are still in the buffer"
                                       % len(self._bits_remaining))

    def finalize(self):
        """Called to finalize writing to a stream, ensuring that remaining bits (used by :class:`BitField`) are
        written to the stream
        :return: the amount of bytes written
        """

        if not self._bits_remaining:
            return 0

        self._bits_remaining.extend([0] * (-len(self._bits_remaining) % 8))
        result = self._write_bits(self._bits_remaining)
        self.discard_bits()
        return result

    def discard_bits(self):
        self._bits_remaining = None

    def read_bits(self, bit_count):
        """Reads the given amount of bits from the stream. It does not necessarily hit the stream, as it is possible
        that the required amount of bits has already been read in a previous call.

        :return: a tuple of the integer representing the read bits, and the amount of bytes read from the stream
            (which may be zero)
        """

        result = []
        read_count = 0
        while len(result) < bit_count:
            # fill the bits_remaining as necessary
            if not self._bits_remaining:
                read = self.raw.read(1)
                read_count += 1
                if not read:
                    raise StreamExhaustedError("Could not parse field, trying to read 1 byte")
                # trick to split each bit in a separate element
                self._bits_remaining = [read[0] >> i & 1 for i in range(7, -1, -1)]

            rem_size = bit_count - len(result)
            result.extend(self._bits_remaining[:rem_size])
            self._bits_remaining = self._bits_remaining[rem_size:]

        # this converts it back to a single integer
        return sum((result[i] << (len(result) - i - 1) for i in range(len(result)))), read_count

    def write_bits(self, value, bit_count):
        """Writes the value with the given amount of bits to the stream. By default, it does not hit the stream, as
        all bit writes are bundled.

        :param value: The value to write to the stream
        :param bit_count: The amount of bits from the value to write to the stream
        :return: the amount of bytes written (always zero unless force_write is True)
        """

        if not self._bits_remaining:
            self._bits_remaining = []
        self._bits_remaining.extend([value >> i & 1 for i in range(bit_count - 1, -1, -1)])

        # write a multiple of 8 bits
        split = len(self._bits_remaining) // 8 * 8
        write, self._bits_remaining = self._bits_remaining[:split], self._bits_remaining[split:]
        return self._write_bits(write)

    def _write_bits(self, bits):
        written = 0
        if len(bits) % 8 != 0:
            raise ValueError("Must write a multiple of 8 bits.")
        if bits:
            number = sum((bits[i] << (len(bits) - i - 1) for i in range(len(bits))))
            written = self.raw.write(number.to_bytes(len(bits) // 8, 'big'))
        return written
