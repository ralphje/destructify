from . import Field, NOT_PROVIDED, StreamExhaustedError
from .base import _retrieve_property


class FixedLengthField(Field):
    length = 0

    def __init__(self, length=NOT_PROVIDED, *args, **kwargs):
        if length is not NOT_PROVIDED:
            self.length = length
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
            related_field = self.structure._meta.get_field_by_name(self.length)
            if not related_field.has_override:
                related_field.override = lambda s, v: len(s[self.name]) if v is None else v

    def get_length(self, context):
        return _retrieve_property(context, self.length)

    def from_stream(self, stream, context=None):
        length = self.get_length(context)
        read = stream.read(length)
        if len(read) < length:
            raise StreamExhaustedError("Could not parse field %s, trying to read %s bytes, but only %s read." %
                                       (self.name, length, len(read)))
        return self.from_bytes(read), length

    def from_bytes(self, value):
        """Method that converts a given bytes object to a Python value. Default implementation just returns the value.
        """
        return value


class TerminatedField(Field):
    def __init__(self, terminator=b'\0', *args, **kwargs):
        self.terminator = terminator
        super().__init__(*args, **kwargs)

    def from_stream(self, stream, context=None):
        length = 0
        read = b""
        while True:
            c = stream.read(1)
            if not c:
                raise StreamExhaustedError("Could not parse field %s; did not find terminator %s" %
                                           (self.name, self.terminator))
            read += c
            length += 1
            if read.endswith(self.terminator):
                break

        return self.from_bytes(read[:-len(self.terminator)]), length

    def from_bytes(self, value):
        return value

    def to_bytes(self, value):
        return value + self.terminator


class StructureField(Field):
    def __init__(self, structure, *args, **kwargs):
        self.sub_structure = structure
        super().__init__(*args, **kwargs)
        if self.default is None:
            self.default = lambda: self.sub_structure()

    def __len__(self):
        return len(self.sub_structure)

    @property
    def ctype(self):
        ctype = self._ctype or self.sub_structure._meta.object_name
        return "{} {}".format(ctype, self.name)

    def from_stream(self, stream, context=None):
        return self.sub_structure.from_stream(stream)

    def to_stream(self, stream, value, context=None):
        if value is None:
            value = self.sub_structure()
        return value.to_stream(stream)


class ArrayField(Field):
    def __init__(self, base_field, size, *args, **kwargs):
        self.base_field = base_field
        self.size = size
        super().__init__(*args, **kwargs)

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

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        self.base_field.name = name

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


class ConditionalField(Field):
    def __init__(self, base_field, condition, *args, **kwargs):
        self.base_field = base_field
        self.condition = condition
        super().__init__(*args, **kwargs)

    def get_condition(self, context):
        return _retrieve_property(context, self.condition)

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {} (conditional)".format(ctype, self.name)

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        self.base_field.name = name

    def from_stream(self, stream, context=None):
        if self.get_condition(context):
            return self.base_field.from_stream(stream, context)
        return None, 0

    def to_stream(self, stream, value, context=None):
        if self.get_condition(context):
            return self.base_field.to_stream(stream, value, context)
        return 0
