import inspect
import io
from contextlib import contextmanager
from functools import total_ordering, partialmethod, partial

from .. import NOT_PROVIDED, FieldContext
from ..exceptions import ImpossibleToCalculateLengthError, DefinitionError
from ..parsing.expression import Expression


def _retrieve_property(context, var, special_case_str=True):
    """Retrieves a property:

    * If the property is callable, and has 0 parameters, it is called without arguments
    * If the property is callable, and has >=1 parameters, it is called with argument context.f
    * If special_case_str=True and var is a str, context[var] is returned
    * Otherwise var is returned
    """
    if callable(var):
        if not isinstance(var, Expression) and len(inspect.signature(var).parameters) == 0:
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
    _creation_counter = 0

    _ctype = None

    def __init__(self, *, name=None, default=NOT_PROVIDED, override=NOT_PROVIDED,
                 decoder=None, encoder=None,
                 offset=None, skip=None, lazy=False):
        self.bound_structure = None

        self.name = name
        self.default = default
        self.override = override
        self.decoder = decoder
        self.encoder = encoder
        self.offset = offset
        self.skip = skip
        self.lazy = lazy

        if offset is not None and skip is not None:
            raise DefinitionError("The field {} specifies both 'offset' and 'skip', which is impossible."
                                  .format(self.full_name))
        if skip is not None and skip < 0:
            raise DefinitionError("The field {} specifies a negative skip, which is impossible."
                                  .format(self.full_name))

        self._creation_counter = Field._creation_counter
        Field._creation_counter += 1

    @property
    def field_context(self):
        """The :class:`FieldContext` that is used in the :class:`ParsingContext` for this field. It returns a partially
        resolved function call with the current field already set.

        :rtype: type
        """
        return partial(FieldContext, self)

    @contextmanager
    def with_name(self, name):
        """Context manager that yields this :class:`Field` with a different name. If `name` is :const:`None`, this is
        ignored.
        """
        old_name = self.name
        if name is not None:
            self.name = name
        try:
            yield self
        finally:
            self.name = old_name

    def _get_property(self, variable_name, context, **kwargs):
        return _retrieve_property(context, getattr(self, variable_name), **kwargs)

    @property
    def full_name(self):
        """The full name of this :class:`Field`."""
        if self.bound_structure is not None:
            return self.bound_structure._meta.structure_name + "." + self.name
        return self.name

    def _seek_length(self):
        """The length of the seek for this field."""
        if self.offset is not None:
            raise ImpossibleToCalculateLengthError()

        if self.skip is not None:
            if isinstance(self.skip, int):
                return self.skip
            else:
                raise ImpossibleToCalculateLengthError()
        return 0

    def __len__(self):
        """You can call :const:`len` on a field to retrieve its byte length. It can either return a value that makes
        sense, or it will raise an :exc:`ImpossibleToCalculateLengthError` when the length depends on something that
        is not known yet.
        """
        raise ImpossibleToCalculateLengthError()

    def _length_sum(self, current_length):
        """This function is used to calculate the length of all fields given the currently calculated length. This
        method is called by ``len(Structure)`` and is in most cases simply an implementation of ``len(self)``.

        This function primarily exists to implement :class:`BitField`.
        """
        try:
            return current_length.__index__() + self._seek_length() + len(self)
        except AttributeError:
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
            return self._creation_counter == other._creation_counter
        return NotImplemented

    def __lt__(self, other):
        # This is needed because bisect does not take a comparison function.
        if isinstance(other, Field):
            return self._creation_counter < other._creation_counter
        return NotImplemented

    def __repr__(self):
        """Display the module, class, and name of the field."""
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__qualname__)
        name = getattr(self, 'name', None)
        if name is not None:
            return '<%s: %s>' % (path, name)
        return '<%s>' % path

    def __str__(self):
        """Display the module, class, and name of the field."""

        if hasattr(self, 'bound_structure') and self.full_name is not None:
            return self.full_name
        elif hasattr(self, 'name') and self.name is not None:
            return self.name
        else:
            return repr(self)

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
    def has_decoder(self):
        return self.decoder is not None

    @property
    def has_encoder(self):
        return self.encoder is not None

    @property
    def ctype(self):
        """A friendly description of the field in the form of a C-style struct definition."""

        ctype = self._ctype or self.__class__.__name__
        return "{} {}".format(ctype, self.name)

    @property
    def preparsable(self):
        """Indicates whether this field is preparsable, i.e. the field is lazy and has an absolute offset set."""

        return self.lazy and self.offset is not None and isinstance(self.offset, int)

    def get_initial_value(self, value, context):
        """Returns the initial value given a context. This is used by :meth:`Structure.from_stream` to retrieve the
        value that is read from the stream. It is called after all fields have been parsed, so inter-field dependencies
        can be resolved here.

        The value may be a proxy object if :attr:`lazy` is set.

        :param value: The value to retrieve the final value for.
        :param ParsingContext context: The context of this field.
        """

        return value

    def get_final_value(self, value, context):
        """Returns the final value given a context. This is used by :meth:`Structure.to_stream` to retrieve the
        value that is to be written to the stream. It is called before any fields have been processed, so inter-field
        dependencies can be resolved here.

        :param value: The value to retrieve the final value for.
        :param ParsingContext context: The context of this field.
        """

        return self.get_overridden_value(value, context)

    def decode_value(self, value, context):
        """This value is called just after the value is retrieved from :meth:`from_stream`. It should return an adjusted
        value that is the true representation of the value

        :param value: The value to retrieve the decoded value for.
        :param ParsingContext context: The context of this field.
        """

        if not self.has_decoder:
            return value
        else:
            return self.decoder(value)

    def encode_value(self, value, context):
        """This value is called just before the value is passed to :meth:`to_stream`. It should return an adjusted
        value that is accepted by :meth:`to_stream`. This is typically used in conjunction with :attr:`encoder`.

        :param value: The value to retrieve the encoded value for.
        :param ParsingContext context: The context of this field.
        """

        if not self.has_encoder:
            return value
        else:
            return self.encoder(value)

    def seek_start(self, stream, context, offset):
        """This is called before the field is parsed/written. It should expect the stream to be aligned to the ending
        of the previous field. It is intended to seek its starting position. This makes sense if the offset is set, for
        instance. In the case this stream is not tellable and no seek is performed, *offset* is returned unmodified.

        Note that the *relative* offset is passed in, but the *absolute* offset is expected as a result.

        :param io.BufferedIOBase stream: The IO stream to consume from.
        :param ParsingContext context: The context used for the parsing.
        :param int offset: The current relative offset in the stream
        :return: The new absolute offset in the stream
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
            if offset % alignment != 0:
                return stream.seek(alignment - (offset % alignment), io.SEEK_CUR)

        # attempt to return the current position if available.
        try:
            return stream.tell()
        except (OSError, AttributeError):
            return offset

    def seek_end(self, stream, context, offset):
        """This is called when the field is lazy and we need to find the end of the field. This is *not* called
        when the field is actually read, as :meth:`from_stream` is expected to align to the end of the field.

        This method should be as efficient as possible with retrieving the length. For instance, if it is possible to
        read a few bytes and then determine how long this field is, that is fine. If it is not possible without reading
        the entire field, this method should return :const:`None`.

        The default implementation is to call ``len(self)`` and use that if possible.

        :param io.BufferedIOBase stream: The IO stream to consume from.
        :param ParsingContext context: The context used for the parsing.
        :param int offset: The current relative offset in the stream
        :return: The new absolute offset in the stream, or None if this field can not be processed without parsing it
                 entirely.
        """
        try:
            return stream.seek(len(self), io.SEEK_CUR)
        except ImpossibleToCalculateLengthError:
            return None

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

    def decode_from_stream(self, stream, context):
        """Shortcut method to calling :meth:`from_stream` and :meth:`decode_value` in succession. Not intended to
        be overridden.
        """

        value, consumed = self.from_stream(stream, context)
        return self.decode_value(value, context), consumed

    def encode_to_stream(self, stream, value, context):
        """Shortcut method to calling :meth:`encode_value` and :meth:`to_stream` in succession. Not intended to
        be overridden.
        """

        return self.to_stream(stream, self.encode_value(value, context), context)

