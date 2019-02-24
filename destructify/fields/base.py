import inspect
from functools import total_ordering

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, ImpossibleToCalculateLengthError, \
    MisalignedFieldError


class _NOT_PROVIDED_META(type):
    def __repr__(self):
        return "NOT_PROVIDED"


class NOT_PROVIDED(metaclass=_NOT_PROVIDED_META):
    pass


def _retrieve_property(context, var, special_case_str=True):
    """Retrieves a property:

    * If the property is callable, and has 0 parameters, it is called without arguments
    * If the property is callable, and has >=1 parameters, it is called with argument context
    * If special_case_str=True and var is a str, context[var] is returned
    * Otherwise var is returned
    """
    if callable(var):
        if len(inspect.signature(var).parameters) == 0:
            return var()
        return var(context)
    elif special_case_str and context is not None and isinstance(var, str):
        return context[var]
    else:
        return var


@total_ordering
class Field:
    """A basic field is incapable of parsing or writing anything, as it is intended to be subclassed."""

    # These track each time a Field instance is created. Used to retain order.
    creation_counter = 0

    _ctype = None

    def __init__(self, *, name=None, default=NOT_PROVIDED, override=NOT_PROVIDED):
        self.bound_structure = None

        self.name = name
        self.default = default
        self.override = override

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    @property
    def full_name(self):
        if self.bound_structure is not None:
            return self.bound_structure.__name__ + "." + self.name
        return self.name

    def __len__(self):
        """You can call :const:`len` on a field to retrieve its byte length. It can either return a value that makes
        sense, or it will raise an :exc:`ImpossibleToCalculateLengthError` when the length depends on something that
        is not known yet.
        """
        raise ImpossibleToCalculateLengthError()

    def initialize(self):
        """Hook that is called after all fields on a structure are loaded, so some additional multi-field things can
        be arranged.
        """
        return

    def contribute_to_class(self, cls, name):
        """Register the field with the model class it belongs to."""

        self.name = name
        self.bound_structure = cls

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

    @property
    def ctype(self):
        """A friendly description of the field in the form of a C-style struct definition."""

        ctype = self._ctype or self.__class__.__name__
        return "{} {}".format(ctype, self.name)

    def get_final_value(self, value, context):
        """Returns the final value given a context. This is used by :meth:`Structure.to_stream` to retrieve the
        value that is to be written to the stream. It is called before any modifications to the value can be made by
        the :class:`Field`.

        :param value: The value to retrieve the final value for.
        :param ParsingContext context: The context of this field.
        """

        return self.get_overridden_value(value, context)

    def from_stream(self, stream, context):
        """Given a stream of bytes object, consumes a given bytes object to Python representation.

        The default implementation is to raise a :exc:`NotImplementedError` and subclasses must override this function.

        :param io.BufferedIOBase stream: The IO stream to consume from. The current position should already be set to
            the total of all previously parsed values.
        :param ParsingContext context: The context of this field.
        :returns: a tuple: the parsed value in its Python representation, and the amount of consumed bytes
        """
        raise NotImplementedError()

    def to_stream(self, stream, value, context):
        """Writes a value to the stream, and returns the amount of bytes written.

        The default implementation is to raise a :exc:`NotImplementedError` and subclasses must override this function.

        :param io.BufferedIOBase stream: The IO stream to write to.
        :param value: The value to write
        :param ParsingContext context: The context of this field.
        :returns: the amount of bytes written
        """

        raise NotImplementedError()
