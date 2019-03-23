import io
import itertools
from functools import partialmethod

from . import Field, FixedLengthField
from ..structures.base import _recapture
from ..parsing import Substream
from ..exceptions import DefinitionError, StreamExhaustedError, ParseError, WriteError, WrongMagicError


class WrappedFieldMixin(object):
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

    def initialize(self):
        self.base_field.name = self.name + ".inner"
        self.base_field.bound_structure = self.bound_structure

        super().initialize()
        self.base_field.initialize()

    @property
    def ctype(self):
        return self._ctype or self.base_field.ctype


class ConstantField(WrappedFieldMixin, Field):
    _take_attributes_from_base = True

    def __init__(self, value, base_field=None, *args, **kwargs):
        if base_field is None:
            if isinstance(value, bytes):
                base_field = FixedLengthField(length=len(value))
            else:
                raise DefinitionError(f"{self} must specify a base_field or a bytes object as default value")

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


class ArrayField(WrappedFieldMixin, Field):
    def __init__(self, base_field, count=None, length=None, until=None, *args, **kwargs):
        self.count = count
        self.length = length
        self.until = until

        if count is None and length is None and until is None:
            raise DefinitionError("%s must specify a count, length or until" % self.full_name)
        elif count is not None and length is not None:
            raise DefinitionError("%s cannot specify both a count and length" % self.full_name)
        elif count is not None and isinstance(count, int) and count < 0:
            raise DefinitionError("%s cannot specify a negative count" % self.full_name)

        super().__init__(base_field, *args, **kwargs)

    def initialize(self):
        """Overrides the content of the length field if possible."""

        super().initialize()

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
            elif length is not None and length >= 0:
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
                    with _recapture(ParseError(f"Error while seeking the start of item {i} in field {self}")):
                        offset = field_instance.seek_start(substream, subcontext, field_start)

                    with _recapture(ParseError(f"Error while parsing item {i} in field {self}")):
                        res, consumed = field_instance.decode_from_stream(substream, subcontext)

                subcontext.fields[i].add_parse_info(value=res, offset=offset, length=consumed)

            except StreamExhaustedError:
                if length is not None and length < 0:
                    # if we have unbounded read, we should just discard the error, otherwise reraise it
                    stream.seek(field_start + total_consumed)
                    del subcontext.fields[i]
                    break
                raise

            else:
                total_consumed += consumed
                result.append(res)

            # Stop when the condition in until is true.
            if self.until is not None and self.until(subcontext, res):
                break

        return result, total_consumed

    def to_stream(self, stream, value, context):
        if value is None:
            value = []
        total_written = 0

        length = None
        if self.count is not None:
            if len(value) != self.get_count(context):
                raise WriteError(f"The count of {self.name} does not match its value.")

        elif self.length is not None:
            length = self.get_length(context)

        field_start = stream.tell()
        substream = Substream(stream)
        subcontext = context.__class__(parent=context, flat=True)
        if self.name in context.fields:
            context.fields[self.name].subcontext = subcontext

        for i, val in enumerate(value):
            if length is not None and length >= 0:
                substream = Substream(stream, stop=field_start + length)

            # Create a new 'field' with a different name, and set it in our context
            subcontext.fields[i] = self.base_field.field_context(context, field_name=i, value=val)

            with self.base_field.with_name(i) as field_instance:
                with _recapture(WriteError(f"Error while seeking the start of item {i} in field {self}")):
                    offset = field_instance.seek_start(substream, subcontext, field_start)

                with _recapture(WriteError(f"Error while parsing item {i} in field {self}")):
                    written = field_instance.encode_to_stream(substream, val, subcontext)

            subcontext.fields[i].add_parse_info(offset=offset, length=written)
            total_written += written

        if length is not None and total_written < length:
            raise WriteError(f"Only {total_written} bytes written in {self.name}, expected {length}.")

        return total_written


class ConditionalField(WrappedFieldMixin, Field):
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


class EnumField(WrappedFieldMixin, Field):
    _take_attributes_from_base = True

    def __init__(self, base_field, enum, *args, **kwargs):
        self.enum = enum
        super().__init__(base_field, *args, **kwargs)

    def __len__(self):
        return len(self.base_field)

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
