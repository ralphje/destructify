import io

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, MisalignedFieldError


class FieldParsingInformation:
    def __init__(self, value, start=None, end=None):
        self.value = value
        self.start = start
        self.end = end


class ParsingContext:
    """A context that is passed around to different methods during reading from and writing to a stream. It is used
    to contain context for the field that is being parsed.
    """

    def __init__(self, *, structure=None, field_values=None, parent=None):
        self.structure = structure
        self.field_values = field_values
        self.parent = parent
        self.parsed_fields = {}
        self.bits_remaining = None

    @property
    def root(self):
        """Retrieves the uppermost :class:`ParsingContext` from this :class:`ParsingContext`. May return itself."""
        root = self
        while root.parent is not None and root.parent != root:
            root = root.parent
        return root

    def __getitem__(self, name):
        """Retrieves the named item from the structure (if known) or (if unknown) from the dict of already parsed
        fields.
        """

        if self.field_values and name in self.field_values:
            return self.field_values[name]
        elif self.structure and hasattr(self.structure, name):
            return getattr(self.structure, name)
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)

    def __getattr__(self, name):
        """Allows you to do context.value instead of context['value']."""
        return self.__getitem__(name)

    def read_stream(self, stream, size=-1, buffer=None):
        """Alias for ``stream.read(size)``, but raises an :exc:`MisalignedFieldError` when bits have still not been
        parsed (used by :class:`BitField`).

        If buffer is set, the stream will be read until EOF or until
        all required bytes are read. This is a little bit overhead, and not required if the stream buffers itself. The
        default (None), will check if there is a read1 method on the stream. If this is the case, it is probably a
        buffered stream and does not require buffering from this function.

        :return: the bytes read
        """
        if self.bits_remaining:
            raise MisalignedFieldError("A field following a BitField is misaligned. %s bits are still in the buffer"
                                       % len(self.bits_remaining))

        if buffer is None:
            # If there is a read1 function on the stream, it is a buffered stream, and we do not require
            # to buffer ourselves.
            buffer = not hasattr(stream, 'read1')

        if buffer:
            result = bytearray()
            while size < 0 or len(result) < size:
                b = stream.read(size)
                if not b:
                    break
                result += b
            return bytes(result)
        else:
            return stream.read(size)

    def write_stream(self, stream, value):
        """Alias for ``stream.write(value)``, but also ensures that remaining bits (used by :class:`BitField`) are
        written to the stream

        :return: the amount of bytes written
        """
        if self.bits_remaining and len(self.bits_remaining) % 8 != 0:
            raise MisalignedFieldError("A field following a BitField is misaligned. %s bits are still in the buffer"
                                       % len(self.bits_remaining))

        return self._write_remaining_bits(stream) + stream.write(value)

    def finalize_stream(self, stream):
        """Called to finalize writing to a stream, ensuring that remaining bits (used by :class:`BitField`) are
        written to the stream

        :return: the amount of bytes written
        """

        return self._write_remaining_bits(stream)

    def read_stream_bits(self, stream, bit_count):
        """Reads the given amount of bits from the stream. It does not necessarily hit the stream, as it is possible
        that the required amount of bits has already been read in a previous call.

        :return: a tuple of the integer representing the read bits, and the amount of bytes read from the stream
            (which may be zero)
        """

        result = []
        read_count = 0
        while len(result) < bit_count:
            # fill the bits_remaining as necessary
            if not self.bits_remaining:
                read = stream.read(1)
                read_count += 1
                if not read:
                    raise StreamExhaustedError("Could not parse bitfield, trying to read 1 byte")
                # trick to split each bit in a separate element
                self.bits_remaining = [read[0] >> i & 1 for i in range(7, -1, -1)]

            rem_size = bit_count - len(result)
            result.extend(self.bits_remaining[:rem_size])
            self.bits_remaining = self.bits_remaining[rem_size:]

        # this converts it back to a single integer
        return sum((result[i] << (len(result) - i - 1) for i in range(len(result)))), read_count

    def write_stream_bits(self, stream, value, bit_count, *, force_write=False):
        """Writes the value with the given amount of bits to the stream. By default, it does not hit the stream, as
        all bit writes are bundled.

        :param stream: The stream to write to
        :param value: The value to write to the stream
        :param bit_count: The amount of bits from the value to write to the stream
        :param bool force_write: If True, all bits are written to the stream, including the previously cached bits.
        :return: the amount of bytes written (always zero unless force_write is True)
        """

        if not self.bits_remaining:
            self.bits_remaining = []
        self.bits_remaining.extend([value >> i & 1 for i in range(bit_count - 1, -1, -1)])

        if force_write:
            return self._write_remaining_bits(stream)
        return 0

    def _write_remaining_bits(self, stream):
        written = 0
        if self.bits_remaining:
            # we align to 8 bits
            self.bits_remaining.extend([0] * (-len(self.bits_remaining) % 8))

            number = sum((self.bits_remaining[i] << (len(self.bits_remaining) - i - 1)
                          for i in range(len(self.bits_remaining))))
            written = stream.write(number.to_bytes(len(self.bits_remaining) // 8, 'big'))
            self.bits_remaining = None

        return written


class Substream:
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
        if item in ('peek', 'read', 'read1', 'readall', 'readinto', 'readinto1', 'readline', 'readlines', 'write') and \
                not hasattr(self.raw, item):
            raise AttributeError()
        return super().__getattribute__(item)

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
        pass  # substream can not be closed

    @property
    def closed(self):
        return self.raw.closed

    def detach(self):
        return self.raw

    def fileno(self):
        return self.raw.fileno()

    def flush(self):
        return self.raw.flush()

    def isatty(self):
        return self.raw.isatty()

    def peek(self, size=-1):
        self._update_position()
        return self.raw.peek(self._cap_amount_of_bytes(size))

    def readable(self):
        return self.raw.readable()

    def _read(self, size, func):
        self._update_position()
        result = func(self._cap_amount_of_bytes(size))
        self._position += len(result)
        return result

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
        result = self.raw.write(b[:length])
        self._position += result
        return result
