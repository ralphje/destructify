import io
import types

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, MisalignedFieldError


class FieldContext:
    def __init__(self, context, value, *, parsed=False, start=None, length=None, stream=None):
        self.context = context
        self.value = value
        self.parsed = parsed
        self.start = start
        self.length = length

        if self.context.capture_raw and stream is not None and length is not None:
            self._capture_raw(stream)

    def _capture_raw(self, stream):
        stream.seek(-self.length, io.SEEK_CUR)
        self.raw = stream.read(self.length)


class ParsingContext:
    """A context that is passed around to different methods during reading from and writing to a stream. It is used
    to contain context for the field that is being parsed.
    """

    def __init__(self, *, structure=None, field_values=None, parent=None, capture_raw=False):
        self.structure = structure
        self.parent = parent
        self.capture_raw = capture_raw
        self.bits_remaining = None

        self.field_values = field_values
        self.f = ParsingContext.F(self)

    class F:
        """A :class:`ParsingContext.F` is a simple object that allows you to access parsed values in the context through
        attribute access.
        """

        def __init__(self, context):
            self.__context = context

        def __getattr__(self, item):
            return self.__context[item]

        def __getitem__(self, name):
            return self.__context[name]

        @property
        def _context(self):
            return self.__context

        @property
        def _(self):
            return self.__context.parent.f

        @property
        def _root(self):
            return self.__context.root.f

    @property
    def field_values(self):
        """Represents a immutable view on **all** field values from :attr:`fields`. This is highly inefficient if you
        only need to access a single value (use ``context[key]``). The resulting dictionary is immutable.

        This attribute is essentially only useful when constructing a new :class:`Structure` where all field values are
        needed.

        Can also be assigned to, to replace all current fields with the specified values, and without additional
        parsing information. This is only useful when constructing a new :class:`ParsingContext` or updating it.

        """
        return types.MappingProxyType({k: v.value for k, v in self.fields.items()})

    @field_values.setter
    def field_values(self, value):
        self.fields = {k: FieldContext(self, v) for k, v in value.items()} if value else {}

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

        if self.fields and name in self.fields:
            return self.fields[name].value
        elif self.structure and hasattr(self.structure, name):
            return getattr(self.structure, name)
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)

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
                b = stream.read(size - len(result))
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
