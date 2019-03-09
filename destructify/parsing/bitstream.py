from destructify.exceptions import MisalignedFieldError, StreamExhaustedError


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
        return getattr(self.raw, item)

    def _check_aligned(self):
        if self._bits_remaining:
            raise MisalignedFieldError("A field following a BitField is misaligned. %s bits are still in the buffer"
                                       % len(self._bits_remaining))

    def flush(self):
        self._check_aligned()
        return self.raw.flush()

    def peek(self, size=-1):
        self._check_aligned()
        return self.raw.peek(size)

    def read(self, size=-1):
        self._check_aligned()
        return self.raw.read(size)

    def read1(self, size=-1):
        self._check_aligned()
        return self.raw.read1(size)

    def readall(self, size=-1):
        self._check_aligned()
        return self.raw.readall(size)

    def readinto(self, size=-1):
        self._check_aligned()
        return self.raw.readinto(size)

    def readinto1(self, size=-1):
        self._check_aligned()
        return self.raw.readinto1(size)

    def readline(self, size=-1):
        self._check_aligned()
        return self.raw.readline(size)

    def readlines(self, size=-1):
        self._check_aligned()
        return self.raw.readlines(size)

    def seek(self, offset, whence=0):
        self._check_aligned()
        return self.raw.seek(offset, whence)

    def write(self, value):
        self._check_aligned()
        return self.raw.write(value)

    def writelines(self, lines):
        self._check_aligned()
        return self.raw.writelines(lines)

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
