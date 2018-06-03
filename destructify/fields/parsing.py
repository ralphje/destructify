import io

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, MisalignedFieldError


class ParsingContext:
    """A context that is passed around to different methods during reading from and writing to a stream. It is used
    to contain context for the field that is being parsed.
    """

    def __init__(self, *, structure=None, parsed_fields=None):
        self.structure = structure
        self.parsed_fields = parsed_fields
        self.bits_remaining = None

    def __getitem__(self, name):
        """Retrieves the named item from the structure (if known) or (if unknown) from the dict of already parsed
        fields.
        """

        if self.structure and hasattr(self.structure, name):
            return getattr(self.structure, name)
        elif self.parsed_fields and name in self.parsed_fields:
            return self.parsed_fields[name]
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)

    def __getattr__(self, name):
        """Allows you to do context.value instead of context['value']."""
        return self.__getitem__(name)

    def read_stream(self, stream, size=-1):
        """Alias for ``stream.read(size)``, but raises an :exc:`MisalignedFieldError` when bits have still not been
        parsed (used by :class:`BitField`)

        :return: the bytes read
        """
        if self.bits_remaining:
            raise MisalignedFieldError("A field following a BitField is misaligned. %s bits are still in the buffer"
                                       % len(self.bits_remaining))

        return stream.read(size)

    def write_stream(self, stream, value):
        """Alias for ``stream.write(value)``, but also ensures that remaining bits (used by :class:`BitField`) are
        written to the stream

        :return: the amount of bytes written
        """

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


class Substream(io.BufferedReader):
    """Represents a view of a subset of a file like object"""

    def __init__(self, raw: io.RawIOBase, start=0, stop=None):
        super().__init__(raw)

        self.start = start
        self.stop = stop

    def _ensure_not_before_start(self):
        if super().tell() < self.start:
            super().seek(self.start, io.SEEK_SET)

    def _cap_amount_of_bytes(self, size):
        if self.stop is None:
            # There is no upper bound, we can read anything
            return size
        else:
            # There is an upper bound in this stream
            max_to_read = self.stop - self.start - self.tell()

            if size is None or size < 0:
                # There is no upper bound on reading, return the amount of bytes until we hit the size limit
                return max_to_read
            return min(max_to_read, size)

    def peek(self, size=-1):
        self._ensure_not_before_start()
        return super().peek(self._cap_amount_of_bytes(size))

    def read(self, size=-1):
        self._ensure_not_before_start()
        return super().read(self._cap_amount_of_bytes(size))

    def read1(self, size):
        self._ensure_not_before_start()
        return super().read1(self._cap_amount_of_bytes(size))

    def readline(self, size=-1):
        self._ensure_not_before_start()
        return super().readline(self._cap_amount_of_bytes(size))

    def seek(self, offset, origin=0):
        current_position = super().tell()

        if origin == io.SEEK_SET:
            super().seek(max(self.start + offset, self.start), io.SEEK_SET)

        elif origin == io.SEEK_CUR:
            super().seek(max(current_position + offset, self.start), io.SEEK_SET)

        elif origin == io.SEEK_END:
            if self.stop is None:
                super().seek(offset, io.SEEK_END)
                self._ensure_not_before_start()  # can't know for sure we are not beyond start boundary
            else:
                super().seek(max(self.stop + offset, self.start), io.SEEK_SET)

        else:
            raise ValueError("Unexpected origin: {}".format(origin))

        return self.tell()

    def tell(self):
        return max(super().tell() - self.start, 0)

    def close(self):
        """Prevent the underlying buffer from being closed."""
        return
