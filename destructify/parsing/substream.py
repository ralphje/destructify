import io


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
