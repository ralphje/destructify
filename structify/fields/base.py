import inspect
from functools import total_ordering

from structify.exceptions import StreamExhaustedError, UnknownDependentFieldError


class NOT_PROVIDED:
    pass


@total_ordering
class Field:
    # These track each time a Field instance is created. Used to retain order.
    creation_counter = 0

    _parse_state = None

    def __init__(self, name=None, default=NOT_PROVIDED, override=NOT_PROVIDED):
        self.structure_cls = None
        self.structure = None

        self.name = name
        self.default = default
        self.override = override

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def contribute_to_class(self, cls, name):
        """Register the field with the model class it belongs to."""

        self.name = name
        self.structure_cls = cls

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

    def get_related_field_value(self, name):
        if self.structure and hasattr(self.structure, name):
            return getattr(self.structure, name)
        elif self._parse_state and name in self._parse_state:
            return self._parse_state[name]
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)

    @property
    def has_default(self):
        return self.default is not NOT_PROVIDED

    def get_default(self):
        if self.has_default:
            if callable(self.default):
                default_func = self.default
            else:
                default_func = lambda: self.default
        else:
            default_func = lambda: None

        if len(inspect.signature(default_func).parameters) == 0:
            return default_func()
        return default_func(self.structure)

    @property
    def has_override(self):
        return self.override is not NOT_PROVIDED

    def get_overridden_value(self, value):
        if self.has_override:
            if callable(self.override):
                default_func = self.override
            else:
                default_func = lambda s, v: self.override
        else:
            return value
        return default_func(self.structure, value)

    def from_stream(self, stream):
        """Given a stream of bytes object, consumes  a given bytes object to Python representation.

        :param io.IOBase stream: The IO stream to consume from. The current position is set to the total of all
            previously parsed values.
        :returns: a tuple: the parsed value in its Python representation, and the amount of consumed bytes
        """
        raise NotImplementedError()

    def to_stream(self, stream, value):
        """Writes a value to the stream, and returns the amount of bytes written

        :param io.IOBase stream: The IO stream to write to.
        :param value: The value to write
        :returns: the amount of bytes written
        """
        value = self.get_overridden_value(value)
        return stream.write(self.to_bytes(value))

    def to_bytes(self, value):
        """Method that converts a given Python representation to bytes. Default implementation assumes the value is
        already bytes.

        This value is a hook for :meth:`to_stream`.
        """
        return value


class FixedLengthReadMixin:
    """Mixin that can be used in conjunction with a :class:`Field` to ease the use of fixed-length fields"""

    length = 0

    def __init__(self, length=NOT_PROVIDED, *args, **kwargs):
        if length is not NOT_PROVIDED:
            self.length = length
        super().__init__(*args, **kwargs)

    def get_length(self):
        if callable(self.length):
            length_func = self.length
        elif isinstance(self.length, str):
            length_func = lambda s: self.get_related_field_value(self.length)
        else:
            return self.length

        if len(inspect.signature(length_func).parameters) == 0:
            return length_func()
        return length_func(self.structure)

    def from_stream(self, stream):
        length = self.get_length()
        read = stream.read(length)
        if len(read) < length:
            raise StreamExhaustedError("Could not parse field %s, trying to read %s bytes, but only %s read." %
                                       (self.name, length, len(read)))
        return self.from_bytes(read), length

    def from_bytes(self, value):
        """Method that converts a given bytes object to a Python value. Default implementation just returns the value.
        """
        return value


class FixedLengthField(FixedLengthReadMixin, Field):
    pass


class StructureField(Field):
    def __init__(self, structure, *args, **kwargs):
        self.struct_cls = structure
        super().__init__(*args, **kwargs)
        if self.default is None:
            self.default = lambda: self.struct_cls()

    def from_stream(self, stream):
        return self.struct_cls.from_stream(stream)

    def to_stream(self, stream, value):
        value = self.get_overridden_value(value)
        if value is None:
            value = self.struct_cls()
        return value.to_stream(stream)
