import struct

from destructify.exceptions import DefinitionError
from . import FixedLengthField


BYTE_ORDER_MAPPING = {
    # native
    '@': '@',
    'native': '@',

    # standard
    '=': '=',
    'std': '=',
    'standard': '=',

    # little-endian
    '<': '<',
    'le': '<',
    'little': '<',
    'little-endian': '<',

    # big-endian
    '>': '>',
    'be': '>',
    'big': '>',
    'big-endian': '>',

    # network-order
    '!': '>',
    'network': '>',
}


class StructField(FixedLengthField):
    format = None
    byte_order = ""

    def __init__(self, format=None, byte_order=None, *args, multibyte=False, **kwargs):

        if format is not None:
            self.format = format
        if byte_order is not None:
            self.byte_order = BYTE_ORDER_MAPPING[byte_order]

        self.multibyte = multibyte

        if self.format[0] in "@=<>!":
            if not self.byte_order:
                self.byte_order = BYTE_ORDER_MAPPING[self.format[0]]
            self.format = self.format[1:]

        self._struct = struct.Struct(self.byte_order + self.format)
        super().__init__(length=self._struct.size, *args, **kwargs)

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)

        # If byte_order is specified in the meta of the structure, we change our own default byte order (if not set)
        if self.bound_structure._meta.byte_order and not self.byte_order:
            try:
                self.byte_order = BYTE_ORDER_MAPPING[self.bound_structure._meta.byte_order]
            except KeyError:
                raise DefinitionError("byte_order %s is invalid" % self.bound_structure._meta.byte_order)
            else:
                self._struct = struct.Struct(self.byte_order + self.format)
                self.length = self._struct.size

    def from_bytes(self, value):
        if self.multibyte:
            return self._struct.unpack(value)
        return self._struct.unpack(value)[0]

    def to_bytes(self, value):
        if value is None:
            value = 0
        if self.multibyte:
            return self._struct.pack(*value)
        return self._struct.pack(value)


def _factory(name, bases=(StructField, ), **kwargs):
    return type(name, bases, kwargs)


CharField = _factory("CharField", format="c", _ctype="char", bases=(StructField,))
ByteField = _factory("ByteField", format="b", _ctype="signed char", bases=(StructField,))
UnsignedByteField = _factory("UnignedByteField", format="unsigned char", _ctype="uint8_t", bases=(StructField,))
BoolField = _factory("BoolField", format="?", _ctype="_Bool", bases=(StructField,))
ShortField = _factory("ShortField", format="h", _ctype="short", bases=(StructField,))
UnsignedShortField = _factory("UnsignedShortField", format="H", _ctype="unsigned short", bases=(StructField,))
IntField = _factory("IntField", format="i", _ctype="int", bases=(StructField,))
UnsignedIntField = _factory("UnsignedIntField", format="I", _ctype="unsigned int", bases=(StructField,))
LongField = _factory("LongField", format="l", _ctype="long", bases=(StructField,))
UnsignedLongField = _factory("UnsignedLongField", format="L", _ctype="unsigned long", bases=(StructField,))
LongLongField = _factory("LongField", format="q", _ctype="long long", bases=(StructField,))
UnsignedLongLongField = _factory("UnsignedLongField", format="Q", _ctype="unsigned long long", bases=(StructField,))
SizeField = _factory("SizeField", format="n", _ctype="ssize_t", bases=(StructField,))
UnsignedSizeField = _factory("UnsignedSizeField", format="N", _ctype="size_t", bases=(StructField,))
HalfPrecisionFloatField = _factory("HalfPrecisionFloatField", format="e", _ctype="binary16",
                                   bases=(StructField,))
FloatField = _factory("FloatField", format="f", _ctype="float", bases=(StructField,))
DoubleField = _factory("DoubleField", format="d", _ctype="double", bases=(StructField,))
