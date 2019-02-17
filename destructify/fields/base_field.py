from . import Field
from ..exceptions import DefinitionError
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
