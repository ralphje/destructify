import io

from . import Field, StreamExhaustedError, Substream, ParsingContext, NOT_PROVIDED
from ..exceptions import DefinitionError, WriteError
from .base import _retrieve_property


class FixedLengthField(Field):
    """Field with a fixed length. It reads exactly the amount of bytes as specified in the length attribute, and
    returns the read bytes directly. Writing is unaffected by the length property.
    """

    def __init__(self, length, *args, strict=True, padding=None, step=1, **kwargs):
        self.length = length
        self.strict = strict
        self.padding = padding
        self.step = step
        super().__init__(*args, **kwargs)

    def __len__(self):
        if isinstance(self.length, int):
            return self.length
        else:
            return super().__len__()

    @property
    def ctype(self):
        if self._ctype:
            return "{} {}".format(self._ctype, self.name)
        else:
            return "{} {}[{}]".format(self.__class__.__name__, self.name, "" if callable(self.length) else self.length)

    def initialize(self):
        """Overrides the content of the length field if possible."""

        if isinstance(self.length, str):
            related_field = self.bound_structure._meta.get_field_by_name(self.length)
            if not related_field.has_override:
                related_field.override = lambda s, v: len(s[self.name]) if v is None else v

    def get_length(self, context):
        return _retrieve_property(context, self.length)

    def from_stream(self, stream, context=None):
        length = self.get_length(context)
        read = context.read_stream(stream, length)
        if len(read) < length and self.strict:
            raise StreamExhaustedError("Could not parse field %s, trying to read %s bytes, but only %s read." %
                                       (self.full_name, length, len(read)))

        # Remove padding
        value = self.from_bytes(read)
        if self.padding is not None:
            while value[-self.step:] == self.padding:
                value = value[:-self.step]

        return value, len(read)

    def to_stream(self, stream, value, context=None):
        length = self.get_length(context)

        if length < 0:
            # For negative lengths, we just write to the stream
            return super().to_stream(stream, value, context)

        val = self.to_bytes(value)

        if len(val) < length:
            if self.padding is not None:
                remaining = length - len(val)

                if self.strict and remaining % self.step != 0:
                    raise WriteError("The field %s must be padded, but the remaining bytes %d are not a multiple of %d." %
                                     (self.full_name, remaining, self.step))

                # slicing for paddings longer than 1 byte
                val = (val + self.padding * remaining)[:length]
            elif self.strict:
                raise WriteError("The contents of %s are %d long, but expecting %d." %
                                 (self.full_name, len(val), length))
        elif len(val) > length:
            if self.strict:
                raise WriteError("The contents of %s are %d long, but expecting %d." %
                                 (self.full_name, len(val), length))

            val = val[:length]

        return super().to_stream(stream, val, context)


class BitField(FixedLengthField):
    """A subclass of :class:`FixedLengthField`, but does not use bytes as the basis, but bits. The field writes and
    reads integers.
    """

    def __init__(self, length, *args, realign=False, **kwargs):
        self.realign = realign
        super().__init__(length, *args, **kwargs)

    def __len__(self):
        if isinstance(self.length, int):
            return self.length / 8
        else:
            return super().__len__()

    @property
    def ctype(self):
        if self._ctype:
            return "{} {}".format(self._ctype, self.name)
        else:
            return "{} {}[{}]".format(self.__class__.__name__, self.name,
                                      "" if callable(self.length) else "{} bits".format(self.length))

    def initialize(self):
        """Overrides the content of the length field if possible."""

        if isinstance(self.length, str):
            related_field = self.bound_structure._meta.get_field_by_name(self.length)
            if not related_field.has_override:
                related_field.override = lambda s, v: s[self.name].bit_length() if v is None else v

    def from_stream(self, stream, context=None):
        result = context.read_stream_bits(stream, self.get_length(context))
        if self.realign:
            context.bits_remaining = None
        return result

    def to_stream(self, stream, value, context=None):
        return context.write_stream_bits(stream, value, self.get_length(context), force_write=self.realign)


class TerminatedField(Field):
    """A field that reads until the :attr:`TerminatedField.terminator` is hit. It directly returns the bytes as read,
     without the terminator.
    """

    def __init__(self, terminator=b'\0', *args, step=1, **kwargs):
        self.terminator = terminator
        self.step = step
        super().__init__(*args, **kwargs)

    def from_stream(self, stream, context=None):
        length = 0
        read = b""
        while True:
            c = context.read_stream(stream, self.step)
            if not c:
                raise StreamExhaustedError("Could not parse field %s; did not find terminator %s" %
                                           (self.name, self.terminator))
            read += c
            length += self.step
            if read.endswith(self.terminator):
                break

        return self.from_bytes(read[:-len(self.terminator)]), length

    def to_bytes(self, value):
        return value + self.terminator


class StringFieldMixin:
    def __init__(self, *args, encoding='utf-8', errors='strict', **kwargs):
        self.encoding = encoding
        self.errors = errors
        super().__init__(*args, **kwargs)

    def from_bytes(self, value):
        return super().from_bytes(value).decode(self.encoding, self.errors)

    def to_bytes(self, value):
        return super().to_bytes(value.encode(self.encoding, self.errors))


class FixedLengthStringField(StringFieldMixin, FixedLengthField):
    pass


class TerminatedStringField(StringFieldMixin, TerminatedField):
    pass


class IntegerField(FixedLengthField):
    def __init__(self, length, byte_order=None, *args, signed=False, **kwargs):
        self.byte_order = byte_order
        self.signed = signed
        super().__init__(length=length, *args, **kwargs)

    def from_bytes(self, value):
        return int.from_bytes(super().from_bytes(value), self.byte_order, signed=self.signed)

    def to_bytes(self, value):
        return super().to_bytes(value.to_bytes(self.length, self.byte_order, signed=self.signed))

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)

        # If byte_order is specified in the meta of the structure, we change our own default byte order (if not set)
        if self.bound_structure._meta.byte_order and not self.byte_order:
            try:
                self.byte_order = self.bound_structure._meta.byte_order
            except KeyError:
                raise DefinitionError("byte_order %s is invalid" % self.bound_structure._meta.byte_order)


class StructureField(Field):
    """A field that contains a :class:`Structure` in itself. If a default is not defined on the field, the default
    is an empty structure.
    """

    def __init__(self, structure, *args, length=None, **kwargs):
        self.structure = structure
        self.length = length

        super().__init__(*args, **kwargs)

        if not self.has_default:
            self.default = lambda: self.structure()

    def __len__(self):
        if isinstance(self.length, int):
            return self.length
        else:
            return len(self.structure)

    @property
    def ctype(self):
        ctype = self._ctype or self.structure._meta.object_name
        return "{} {}".format(ctype, self.name)

    def get_length(self, context):
        return _retrieve_property(context, self.length)

    def from_stream(self, stream, context):
        length = None
        if self.length is not None:
            length = self.get_length(context)

        with Substream(stream,
                       start=stream.tell(),
                       stop=stream.tell() + length if length is not None else None) as substream:
            res, consumed = self.structure.from_stream(substream, context=ParsingContext(parent=context))

        if length is not None and consumed < length:
            stream.seek(length - consumed, io.SEEK_CUR)
            consumed = length
        return res, consumed

    def to_stream(self, stream, value, context=None):
        if value is None:
            value = self.structure()
        return value.to_stream(stream)


class BaseFieldMixin(object):
    def __init__(self, base_field, *args, **kwargs):
        self.base_field = base_field

        super().__init__(*args, **kwargs)

        if not isinstance(base_field, Field):
            raise DefinitionError("You must initialize the base_field property of %s with a Field-type object, "
                                  "not a %s." % (self.full_name, base_field.__class__.__name__))

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        self.base_field.name = name
        self.base_field.bound_structure = cls

    @property
    def ctype(self):
        return self._ctype or self.base_field.ctype


class ArrayField(BaseFieldMixin, Field):
    """A field that repeats the provided base field multiple times."""

    def __init__(self, base_field, size, *args, **kwargs):
        self.size = size
        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        if isinstance(self.size, int):
            return self.size * len(self.base_field)
        else:
            return super().__len__()

    def get_size(self, context):
        return _retrieve_property(context, self.size)

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {}[{}]".format(ctype, self.name, "" if callable(self.size) else self.size)

    def from_stream(self, stream, context=None):
        result = []
        total_consumed = 0
        for i in range(0, self.get_size(context)):
            res, consumed = self.base_field.from_stream(stream, context)
            total_consumed += consumed
            result.append(res)
        return result, total_consumed

    def to_stream(self, stream, value, context=None):
        if value is None:
            value = []

        total_written = 0
        for val in value:
            total_written += self.base_field.to_stream(stream, val, context)
        return total_written


class ConditionalField(BaseFieldMixin, Field):
    """A field that may or may not be present. When the :attr:`condition` evaluates to true, the :attr:`base_field`
    field is parsed, otherwise the field is :const:`None`.

    """

    def __init__(self, base_field, condition, *args, **kwargs):
        self.condition = condition
        super().__init__(base_field, *args, **kwargs)

    def get_condition(self, context):
        return _retrieve_property(context, self.condition)

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {} (conditional)".format(ctype, self.name)

    def from_stream(self, stream, context=None):
        if self.get_condition(context):
            return self.base_field.from_stream(stream, context)
        return None, 0

    def to_stream(self, stream, value, context=None):
        if self.get_condition(context):
            return self.base_field.to_stream(stream, value, context)
        return 0


class EnumField(BaseFieldMixin, Field):
    """A field that takes the value as evaluated by the :attr:`base_field` and parses it as the provided :attr:`enum`.
    """

    def __init__(self, base_field, enum, *args, **kwargs):
        self.enum = enum
        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        return self.base_field.__len__()

    def from_stream(self, stream, context=None):
        value, length = self.base_field.from_stream(stream, context)
        return self.enum(value), length

    def to_stream(self, stream, value, context=None):
        if hasattr(value, 'value'):
            value = value.value
        return self.base_field.to_stream(stream, value, context)
