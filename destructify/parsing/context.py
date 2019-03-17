import io
import types

from destructify import NOT_PROVIDED
from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, MisalignedFieldError


class ParsingContext:
    """A context that is passed around to different methods during reading from and writing to a stream. It is used
    to contain context for the field that is being parsed.
    """

    def __init__(self, structure=None, *, parent=None, flat=False, stream=None, capture_raw=False):
        self.parent = parent
        self.flat = flat
        self.stream = stream
        self.capture_raw = capture_raw
        self.done = False

        self.fields = {}
        self.f = ParsingContext.F(self)

        if structure:
            self.initialize_from_meta(structure._meta)

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
            if self.__context.parent:
                return self.__context.parent.f

        @property
        def _root(self):
            return self.__context.root.f

    def initialize_from_meta(self, meta, structure=None):
        """Adds fields to the context based on the provided StructureOptions. If *structure* is provided, the values
        in the structure are passed as values to the field contexts
        """
        self.fields = {}
        for field in meta.fields:
            value = NOT_PROVIDED
            if structure and hasattr(structure, field.name):
                value = getattr(structure, field.name)
            self.fields[field.name] = field.field_context(self, value=value)

        self.capture_raw = self.capture_raw or meta.capture_raw

    def _add_values(self, values):
        """Method for easily adding :class:`FieldContext` objects to this context. Used only by testing."""
        if values:
            for f, v in values.items():
                self.fields[f] = FieldContext(None, self, v)
        return self

    @property
    def field_values(self):
        """Represents a immutable view on **all** field values from :attr:`fields`. This is highly inefficient if you
        only need to access a single value (use ``context[key]``). The resulting dictionary is immutable.

        This attribute is essentially only useful when constructing a new :class:`Structure` where all field values are
        needed.

        """
        return types.MappingProxyType({k: v.value for k, v in self.fields.items()})

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

        if self.fields and name in self.fields and self.fields[name].has_value:
            return self.fields[name].value
        elif self.flat and self.parent is not None:
            return self.parent[name]
        else:
            raise UnknownDependentFieldError("Dependent field %s is not loaded yet, so can't be used." % name)


class FieldContext:
    """This class contains information about the parsing state of the specified field."""

    def __init__(self, field, context, value=NOT_PROVIDED, *, parsed=False, offset=None, length=None, lazy=False,
                 raw=None):
        self.context = context
        self.field = field
        self._value = value
        self.parsed = parsed
        self.offset = offset
        self.length = length
        self.lazy = lazy
        self.raw = raw
        self.subcontext = None

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)

    def __str__(self):
        values = []
        for attr in ('field', 'parsed', 'offset', 'length', 'subcontext'):
            values.append("%s=%r" % (attr, getattr(self, attr)))
        values.insert(1, ('value=%r' % self._value) if not self.lazy else 'value=(lazy)')
        return '%s(%s)' % (self.__class__.__name__, ", ".join(values))

    @property
    def resolved(self):
        """Returns whether the value has been resolved from/written to the stream, i.e. is not lazy anymore."""
        return self.parsed and not self.lazy

    @property
    def has_value(self):
        """Returns whether the value is present."""
        return self.lazy or self._value is not NOT_PROVIDED

    @property
    def value(self):
        """Returns the value that is to be used. May be a lazy proxy object."""
        if not self.has_value:
            raise ValueError("This field has currently no value.")

        if self.lazy:
            import lazy_object_proxy
            return lazy_object_proxy.Proxy(self._lazy_get)
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def _lazy_get(self):
        current_offset = self.context.stream.tell()
        self.context.stream.seek(self.offset)
        try:
            value, length = self.field.decode_from_stream(self.context.stream, self.context)
            # if the context is not yet done, we can update the field to its final value
            if not self.context.done:
                self.add_parse_info(offset=self.offset, length=length, value=value, lazy=False)
            return value
        finally:
            self.context.stream.seek(current_offset)

    def add_parse_info(self, offset, length, value=NOT_PROVIDED, lazy=False):
        """Call that is used when the value has been parsed. This fills all information in te structure.

        :param value: The value that has been parsed.
        :param offset: The offset of the value in the stream
        :param length: The length of the value in the stream
        :param lazy: Indicates whether the value is lazily loaded, i.e. the stream is not hit (value is ignored)
        """
        if value is NOT_PROVIDED and not self.has_value and not lazy:
            raise ValueError("add_parse_info requires value to be set if not lazy")

        self.parsed = True
        if value is not NOT_PROVIDED:
            self._value = value
        self.offset = offset
        self.length = length
        self.lazy = lazy

        if self.context.capture_raw and self.context.stream is not None and length is not None and not lazy:
            self._capture_raw(self.context.stream)

    def _capture_raw(self, stream):
        stream.seek(-self.length, io.SEEK_CUR)
        self.raw = stream.read(self.length)
