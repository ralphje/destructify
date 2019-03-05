import inspect
import io
from functools import total_ordering

from destructify.exceptions import ImpossibleToCalculateLengthError, DefinitionError


class _NOT_PROVIDED_META(type):
    def __repr__(self):
        return "NOT_PROVIDED"


class NOT_PROVIDED(metaclass=_NOT_PROVIDED_META):
    pass


def _retrieve_property(context, var, special_case_str=True):
    """Retrieves a property:

    * If the property is callable, and has 0 parameters, it is called without arguments
    * If the property is callable, and has >=1 parameters, it is called with argument context.f
    * If special_case_str=True and var is a str, context[var] is returned
    * Otherwise var is returned
    """
    if callable(var):
        if len(inspect.signature(var).parameters) == 0:
            return var()
        return var(context.f)
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

    def __init__(self, *, name=None, default=NOT_PROVIDED, override=NOT_PROVIDED, offset=None, skip=None):
        self.bound_structure = None

        self.name = name
        self.default = default
        self.override = override
        self.offset = offset
        self.skip = skip

        if offset is not None and skip is not None:
            raise DefinitionError("The field {} specifies both 'offset' and 'skip', which is impossible."
                                  .format(self.full_name))
        if skip is not None and skip < 0:
            raise DefinitionError("The field {} specifies a negative skip, which is impossible."
                                  .format(self.full_name))

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    @property
    def full_name(self):
        if self.bound_structure is not None:
            return self.bound_structure._meta.structure_name + "." + self.name
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
            return self.override(context.f, value)
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

    def seek_start(self, stream, context, position):
        """This is called before the field is parsed/written. It should expect the stream to be aligned to the ending
        of the previous field. It is intended to seek its starting position. This makes sense if the offset is set, for
        instance. In the case this stream is not tellable and no seek is performed, *position* is returned unmodified.

        :param io.BufferedIOBase stream: The IO stream to consume from.
        :param ParsingContext context: The context used for the parsing.
        :param int position: The current position in the stream according to the internal counter.
        :return: The new position.
        """
        if self.offset is not None:
            offset = _retrieve_property(context, self.offset)
            if offset is not None:
                if offset < 0:
                    return stream.seek(offset, io.SEEK_END)
                else:
                    return stream.seek(offset, io.SEEK_SET)

        elif self.skip is not None:
            skip = _retrieve_property(context, self.skip)
            if skip is not None:
                return stream.seek(skip, io.SEEK_CUR)

        elif self.bound_structure is not None and self.bound_structure._meta.alignment is not None:
            # align to the bytes of the alignment of the options
            alignment = self.bound_structure._meta.alignment
            if position % alignment != 0:
                return stream.seek(alignment - (position % alignment), io.SEEK_CUR)

        # attempt to return the current position if available.
        try:
            return stream.tell()
        except (OSError, AttributeError):
            return position

    def from_stream(self, stream, context):
        """Given a stream of bytes object, consumes a given bytes object to Python representation. The given stream
        is already at the start of the field. This method must ensure that the stream is after the end position of the
        field after reading. In other words, the following will typically hold true::

            stream_at_start.tell() + result[1] == stream_at_end.tell()

        The default implementation is to raise a :exc:`NotImplementedError` and subclasses must override this function.

        :param io.BufferedIOBase stream: The IO stream to consume from. The current position is already set to the start
            position of the field.
        :param ParsingContext context: The context of this field.
        :returns: a tuple: the parsed value in its Python representation, and the amount of consumed bytes
        """
        raise NotImplementedError()

    def to_stream(self, stream, value, context):
        """Writes a value to the stream, and returns the amount of bytes written. The given stream will already be
        at the start of the field, and this method must ensure that the stream cursor is after the end position of the
        field. In other words::

            stream_at_start.tell() + result == stream_at_end.tell()

        The default implementation is to raise a :exc:`NotImplementedError` and subclasses must override this function.

        :param io.BufferedIOBase stream: The IO stream to write to.
        :param value: The value to write
        :param ParsingContext context: The context of this field.
        :returns: the amount of bytes written
        """

        raise NotImplementedError()
