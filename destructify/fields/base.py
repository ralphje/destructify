import inspect
from functools import total_ordering

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError


class NOT_PROVIDED:
    pass


def _retrieve_property(context, var, special_case_str=True):
    """Retrieves a property:

    * If the property is callable, and has 0 parameters, it is called without arguments
    * If the property is callable, and has 0 parameters, it is called with argument context
    * If special_case_str=True and var is a str, context[var] is returned
    * Otherwise var is returned
    """
    if callable(var):
        if len(inspect.signature(var).parameters) == 0:
            return var()
        return var(context)
    elif special_case_str and isinstance(var, str):
        return context[var]
    else:
        return var


@total_ordering
class Field:
    # These track each time a Field instance is created. Used to retain order.
    creation_counter = 0

    _parse_state = None

    def __init__(self, name=None, default=NOT_PROVIDED, override=NOT_PROVIDED):
        self.structure = None

        self.name = name
        self.default = default
        self.override = override

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def initialize(self):
        """Hook that is called after all fields on a structure are loaded, so some additional multi-field things can
        be arranged.
        """
        return

    def contribute_to_class(self, cls, name):
        """Register the field with the model class it belongs to."""

        self.name = name
        self.structure = cls

        cls._meta.add_field(self)

    def __eq__(self, other):
        # Needed for @total_ordering
        if isinstance(other, Field):
            return self.creation_counter == other.creation_counter
        return NotImplemented

    def __lt__(self, other):
        # This is needed because bisect does not take a comparison function.
        if isinstance(other, Field):
            return self.creation_counter < other.creation_counter
        return NotImplemented

    def __repr__(self):
        """Display the module, class, and name of the field."""
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__qualname__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path

    @property
    def has_default(self):
        return self.default is not NOT_PROVIDED

    def get_default(self, context):
        if not self.has_default:
            return None
        return _retrieve_property(context, self.default, special_case_str=False)

    @property
    def has_override(self):
        return self.override is not NOT_PROVIDED

    def get_overridden_value(self, value, context):
        if not self.has_override:
            return value
        elif callable(self.override):
            return self.override(context, value)
        else:
            return self.override

    def get_final_value(self, value, context=None):
        return self.get_overridden_value(value, context)

    def from_stream(self, stream, context=None):
        """Given a stream of bytes object, consumes  a given bytes object to Python representation.

        :param io.BufferedIOBase stream: The IO stream to consume from. The current position is set to the total of all
            previously parsed values.
        :param FieldContext context: The context of this field.
        :returns: a tuple: the parsed value in its Python representation, and the amount of consumed bytes
        """
        raise NotImplementedError()

    def to_stream(self, stream, value, context=None):
        """Writes a value to the stream, and returns the amount of bytes written

        :param io.BufferedIOBase stream: The IO stream to write to.
        :param value: The value to write
        :param FieldContext context: The context of this field.
        :returns: the amount of bytes written
        """

        return stream.write(self.to_bytes(value))

    def to_bytes(self, value):
        """Method that converts a given Python representation to bytes. Default implementation assumes the value is
        already bytes.

        This value is a hook for :meth:`to_stream`.
        """
        return value


class FieldContext:
    def __init__(self, *, structure=None, parsed_fields=None):
        self.structure = structure
        self.parsed_fields = parsed_fields

    def __getitem__(self, name):
        if self.structure and hasattr(self.structure, name):
            return getattr(self.structure, name)
        elif self.parsed_fields and name in self.parsed_fields:
            return self.parsed_fields[name]
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)

    def __getattr__(self, name):
        """Allows you to do context.value instead of context['value']."""
        return self.__getitem__(name)


class FixedLengthField(Field):
    length = 0

    def __init__(self, length=NOT_PROVIDED, *args, **kwargs):
        if length is not NOT_PROVIDED:
            self.length = length
        super().__init__(*args, **kwargs)

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

    def get_size(self, context):
        return _retrieve_property(context, self.size)

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        self.base_field.name = name
        self.base_field.structure_cls = cls

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
