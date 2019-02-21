from . import Field, Substream
from ..exceptions import DefinitionError, StreamExhaustedError, ParseError, WriteError
from .base import _retrieve_property


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

    def __init__(self, base_field, count=None, length=None, *args, **kwargs):
        self.count = count
        self.length = length

        if count is None and length is None:
            raise DefinitionError("%s must specify a count or a length" % self.full_name)
        elif count is not None and length is not None:
            raise DefinitionError("%s cannot specify both a count and length" % self.full_name)

        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        if isinstance(self.count, int):
            return self.count * len(self.base_field)
        elif isinstance(self.length, int):
            return self.length
        else:
            return super().__len__()

    def get_count(self, context):
        return _retrieve_property(context, self.count)

    def get_length(self, context):
        return _retrieve_property(context, self.length)

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {}[{}]".format(ctype, self.name, "" if callable(self.count) else self.count)

    def from_stream(self, stream, context=None):
        result = []
        total_consumed = 0
        if self.count:
            count = self.get_count(context)
            for i in range(0, count):
                res, consumed = self.base_field.from_stream(stream, context)
                total_consumed += consumed
                result.append(res)

        elif self.length:
            length = self.get_length(context)

            field_start = stream.tell()
            if length >= 0:
                while total_consumed < length:
                    with Substream(stream, start=stream.tell(), stop=field_start + length) as substream:
                        res, consumed = self.base_field.from_stream(substream, context)
                    total_consumed += consumed
                    result.append(res)
            else:
                while True:
                    try:
                        res, consumed = self.base_field.from_stream(stream, context)
                        total_consumed += consumed
                        result.append(res)
                    except StreamExhaustedError:
                        stream.seek(field_start + total_consumed)
                        break

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


class SwitchField(Field):
    def __init__(self, cases, switch, *args, other=None, **kwargs):
        self.cases = cases
        self.switch = switch
        self.other = other

        super().__init__(*args, **kwargs)

        if not all((isinstance(f, Field) for f in self.cases.values())):
            raise DefinitionError("You must initialize the cases property of %s with Field values." % (self.full_name,))
        if self.other is not None and not isinstance(self.other, Field):
            raise DefinitionError("You must initialize the default property of %s with a Field." % (self.full_name,))

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        for f in self.cases.values():
            f.name = name
            f.bound_structure = cls
        if self.other is not None:
            self.other.name = name
            self.other.bound_structure = cls

    def get_switch(self, context):
        return _retrieve_property(context, self.switch)

    @property
    def ctype(self):
        return "switch {}".format(self.name)

    def from_stream(self, stream, context=None):
        switch = self.get_switch(context)
        if switch in self.cases:
            return self.cases[switch].from_stream(stream, context)
        if self.other is not None:
            return self.other.from_stream(stream, context)
        raise ParseError("The case {} is not specified for {}, and other is unset".format(switch, self.full_name))

    def to_stream(self, stream, value, context=None):
        switch = self.get_switch(context)
        if switch in self.cases:
            return self.cases[switch].to_stream(stream, value, context)
        if self.other is not None:
            return self.other.to_stream(stream, value, context)
        raise WriteError("The case {} is not specified for {}, and other is unset".format(switch, self.full_name))
