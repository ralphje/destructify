import copy
import io
import itertools
from functools import partialmethod, partial

from destructify.structures.base import _recapture
from . import Field, Substream, FixedLengthField, FieldContext
from ..exceptions import DefinitionError, StreamExhaustedError, ParseError, WriteError, WrongMagicError


class BaseFieldMixin(object):
    _take_attributes_from_base = False

    def __init__(self, base_field, *args, **kwargs):
        self.base_field = base_field

        super().__init__(*args, **kwargs)

        if not isinstance(base_field, Field):
            raise DefinitionError("You must initialize the base_field property of %s with a Field-type object, "
                                  "not a %s." % (self.full_name, base_field.__class__.__name__))

        if self._take_attributes_from_base:
            if self.base_field.has_default and not self.has_default:
                self.default = self.base_field.default
            if self.base_field.has_override and not self.has_override:
                self.override = self.base_field.override

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        self.base_field.name = name
        self.base_field.bound_structure = cls

    @property
    def ctype(self):
        return self._ctype or self.base_field.ctype


class ConstantField(BaseFieldMixin, Field):
    _take_attributes_from_base = True

    def __init__(self, value, base_field=None, *args, **kwargs):
        if base_field is None:
            if isinstance(value, bytes):
                base_field = FixedLengthField(length=len(value))
            else:
                raise DefinitionError("{} must specify a base_field or a bytes object as default value".format(self))

        self.value = value
        kwargs.setdefault("default", self.value)

        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        return len(self.base_field)

    def from_stream(self, stream, context):
        value, length = self.base_field.decode_from_stream(stream, context)

        if value != self.value:
            raise WrongMagicError("The constant is incorrect for {}".format(self.full_name))

        return value, length

    def to_stream(self, stream, value, context):
        if value != self.value:
            raise WriteError("The constant is incorrect for {}".format(self.full_name))
        return self.base_field.encode_to_stream(stream, value, context)


class ArrayField(BaseFieldMixin, Field):
    def __init__(self, base_field, count=None, length=None, *args, **kwargs):
        self.count = count
        self.length = length

        if count is None and length is None:
            raise DefinitionError("%s must specify a count or a length" % self.full_name)
        elif count is not None and length is not None:
            raise DefinitionError("%s cannot specify both a count and length" % self.full_name)
        elif count is not None and isinstance(count, int) and count < 0:
            raise DefinitionError("%s cannot specify a negative count" % self.full_name)

        super().__init__(base_field, *args, **kwargs)

    def initialize(self):
        """Overrides the content of the length field if possible."""

        if isinstance(self.count, str):
            related_field = self.bound_structure._meta.get_field_by_name(self.count)
            if not related_field.has_override:
                related_field.override = lambda c, v: len(c[self.name])

    def __len__(self):
        if isinstance(self.count, int):
            return self.count * len(self.base_field)
        elif isinstance(self.length, int):
            return self.length
        else:
            return super().__len__()

    get_count = partialmethod(Field._get_property, 'count')
    get_length = partialmethod(Field._get_property, 'length')

    def seek_end(self, stream, context, offset):
        if self.length is not None:
            return stream.seek(self.get_length(context), io.SEEK_CUR)

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {}[{}]".format(ctype, self.name, "" if callable(self.count) else self.count)

    def from_stream(self, stream, context):
        result = []
        total_consumed = 0

        # If count is specified, we read the specified amount of times from the stream.
        # otherwise we need to consume the length
        count = length = None
        if self.count is not None:
            count = self.get_count(context)
        elif self.length is not None:
            length = self.get_length(context)

        field_start = stream.tell()
        substream = Substream(stream)
        subcontext = context.__class__(parent=context, flat=True)
        if self.name in context.fields:
            context.fields[self.name].subcontext = subcontext

        for i in itertools.count():
            if count is not None:
                # if count is set, we only read the <count> amount of times
                if count <= i:
                    break
            elif length >= 0:
                # if length is positive, we read <length> amount of bytes
                if total_consumed >= length:
                    break
                substream = Substream(stream, stop=field_start + length)
            else:
                # for unbounded read, we expect to encounter an exception somewhere down the line
                pass

            # Create a new 'field' with a different name, and set it in our context
            subcontext.fields[i] = self.base_field.field_context(context, field_name=i)

            try:
                with self.base_field.with_name(i) as field_instance:
                    with _recapture(ParseError("Error while seeking the start of item {} in field {}"
                                               .format(i, self.full_name))):
                        offset = field_instance.seek_start(substream, subcontext, field_start)

                    with _recapture(ParseError("Error while parsing item {} in field {}".format(i, self.full_name))):
                        res, consumed = field_instance.decode_from_stream(substream, subcontext)

                subcontext.fields[i].add_parse_info(value=res, offset=offset, length=consumed)

            except StreamExhaustedError:
                if length < 0:
                    # if we have unbounded read, we should just discard the error, otherwise reraise it
                    stream.seek(field_start + total_consumed)
                    del subcontext.fields[i]
                    break
                raise

            else:
                total_consumed += consumed
                result.append(res)

        return result, total_consumed

    def to_stream(self, stream, value, context):
        if value is None:
            value = []

        # TODO: handle length and count

        total_written = 0
        for val in value:
            total_written += self.base_field.encode_to_stream(stream, val, context)
        return total_written


class ConditionalField(BaseFieldMixin, Field):
    _take_attributes_from_base = True

    def __init__(self, base_field, condition, *args, fallback=None, **kwargs):
        self.condition = condition
        self.fallback = fallback
        super().__init__(base_field, *args, **kwargs)

    get_condition = partialmethod(Field._get_property, 'condition')

    @property
    def ctype(self):
        ctype = self._ctype or self.base_field.ctype.split(" ")[0]
        return "{} {} (conditional)".format(ctype, self.name)

    def from_stream(self, stream, context):
        if self.get_condition(context):
            return self.base_field.decode_from_stream(stream, context)
        return self.fallback, 0

    def to_stream(self, stream, value, context):
        if self.get_condition(context):
            return self.base_field.encode_to_stream(stream, value, context)
        return 0


class EnumField(BaseFieldMixin, Field):
    _take_attributes_from_base = True

    def __init__(self, base_field, enum, *args, **kwargs):
        self.enum = enum
        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        return self.base_field.__len__()

    def from_stream(self, stream, context):
        value, length = self.base_field.decode_from_stream(stream, context)
        return self.enum(value), length

    def to_stream(self, stream, value, context):
        if isinstance(value, self.enum):
            value = value.value
        elif isinstance(value, str):
            try:
                value = self.enum[value].value
            except KeyError:
                pass
        return self.base_field.encode_to_stream(stream, value, context)


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

    get_switch = partialmethod(Field._get_property, 'switch')

    @property
    def ctype(self):
        return "switch {}".format(self.name)

    def from_stream(self, stream, context):
        switch = self.get_switch(context)
        if switch in self.cases:
            return self.cases[switch].decode_from_stream(stream, context)
        if self.other is not None:
            return self.other.decode_from_stream(stream, context)
        raise ParseError("The case {} is not specified for {}, and other is unset".format(switch, self.full_name))

    def to_stream(self, stream, value, context):
        switch = self.get_switch(context)
        if switch in self.cases:
            return self.cases[switch].encode_to_stream(stream, value, context)
        if self.other is not None:
            return self.other.encode_to_stream(stream, value, context)
        raise WriteError("The case {} is not specified for {}, and other is unset".format(switch, self.full_name))
