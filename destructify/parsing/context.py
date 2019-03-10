import io
import types

from destructify.exceptions import StreamExhaustedError, UnknownDependentFieldError, MisalignedFieldError


class FieldContext:
    def __init__(self, context, value=None, *, parsed=False, offset=None, length=None, stream=None,
                 field=None, lazy=False):
        self.context = context
        self._value = value
        self.parsed = parsed
        self.offset = offset
        self.length = length
        self.stream = stream
        self.field = field
        self.lazy = lazy

        if self.context.capture_raw and stream is not None and length is not None and not lazy:
            self._capture_raw(stream)

    def _lazy_get(self):
        current_offset = self.stream.tell()
        self.stream.seek(self.offset)
        try:
            result = self.field.from_stream(self.stream, self.context)
            # if the context is not yet done, we can update the field to its final value
            if not self.context.done:
                self._value = result[0]
                self.length = result[1]
                self.lazy = False
            return result[0]
        finally:
            self.stream.seek(current_offset)

    @property
    def value(self):
        if self.lazy:
            import lazy_object_proxy
            return lazy_object_proxy.Proxy(self._lazy_get)
        return self._value

    def _capture_raw(self, stream):
        stream.seek(-self.length, io.SEEK_CUR)
        self.raw = stream.read(self.length)


class ParsingContext:
    """A context that is passed around to different methods during reading from and writing to a stream. It is used
    to contain context for the field that is being parsed.
    """

    def __init__(self, *, structure=None, field_values=None, parent=None, capture_raw=False, done=False):
        self.structure = structure
        self.parent = parent
        self.capture_raw = capture_raw
        self.done = done

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

