import struct

from destructify.exceptions import DefinitionError
from . import FixedLengthField, NOT_PROVIDED


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

    def __init__(self, format=NOT_PROVIDED, byte_order=NOT_PROVIDED, *args, **kwargs):

        if format is not NOT_PROVIDED:
            self.format = format
        if byte_order is not NOT_PROVIDED:
            self.byte_order = byte_order

        if self.format[0] in "@=<>!":
            if not self.byte_order:
                self.byte_order = self.format[0]
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
        return self._struct.unpack(value)[0]

    def to_bytes(self, value):
        if value is None:
            value = 0
        return self._struct.pack(value)


def _factory(name, bases=(StructField, ), **kwargs):
    return type(name, bases, kwargs)


LittleEndianStructField = _factory("LittleEndianStructField", byte_order="<", bases=(StructField, ))
BigEndianStructField = _factory("BigEndianStructField", byte_order=">", bases=(StructField, ))
StandardStructField = _factory("StandardStructField", byte_order="=", bases=(StructField, ))
NativeStructField = _factory("NativeStructField", byte_order="@", bases=(StructField, ))

CharField = _factory("CharField", format="c", _ctype="char", bases=(StructField,))
NativeCharField = _factory("NativeCharField", _ctype="char", bases=(NativeStructField, CharField))

ByteField = _factory("ByteField", format="b", _ctype="int8_t", bases=(StructField,))
NativeByteField = _factory("SignedByteField", _ctype="signed char", bases=(NativeStructField, ByteField))

UnsignedByteField = _factory("UnignedByteField", format="B", _ctype="uint8_t", bases=(StructField,))
NativeUnsignedByteField = _factory("NativeSignedByteField", _ctype="unsigned char",
                                   bases=(NativeStructField, UnsignedByteField))

BoolField = _factory("BoolField", format="?", _ctype="_Bool", bases=(StructField,))
NativeBoolField = _factory("NativeBoolField", bases=(NativeStructField, BoolField))

ShortField = _factory("ShortField", format="h", _ctype="int16_t", bases=(StructField,))
LEShortField = _factory("LEShortField", bases=(LittleEndianStructField, ShortField))
BEShortField = _factory("BEShortField", bases=(BigEndianStructField, ShortField))
StandardShortField = _factory("StandardShortField", bases=(StandardStructField, ShortField))
NativeShortField = _factory("NativeShortField", _ctype="short", bases=(NativeStructField, ShortField))

UnsignedShortField = _factory("UnsignedShortField", format="H", _ctype="uint16_t", bases=(StructField,))
LEUnsignedShortField = _factory("LEUnsignedShortField", bases=(LittleEndianStructField, UnsignedShortField))
BEUnsignedShortField = _factory("BEUnsignedShortField", bases=(BigEndianStructField, UnsignedShortField))
StandardUnsignedShortField = _factory("StandardUnsignedShortField", bases=(StandardStructField, UnsignedShortField))
NativeUnsignedShortField = _factory("NativeUnsignedShortField", _ctype="unsigned short",
                                    bases=(NativeStructField, UnsignedShortField))

IntField = _factory("IntField", format="i", _ctype="int32_t", bases=(StructField,))
LEIntField = _factory("LEIntField", bases=(LittleEndianStructField, IntField))
BEIntField = _factory("BEIntField", bases=(BigEndianStructField, IntField))
StandardIntField = _factory("StandardIntField", bases=(StandardStructField, IntField))
NativeIntField = _factory("NativeIntField", _ctype="int", bases=(NativeStructField, IntField))

UnsignedIntField = _factory("UnsignedIntField", format="I", _ctype="uint32_t", bases=(StructField,))
LEUnsignedIntField = _factory("LEUnsignedIntField", bases=(LittleEndianStructField, UnsignedIntField))
BEUnsignedIntField = _factory("BEUnsignedIntField", bases=(BigEndianStructField, UnsignedIntField))
StandardUnsignedIntField = _factory("StandardUnsignedIntField",
                                        bases=(StandardStructField, UnsignedIntField))
NativeUnsignedIntField = _factory("NativeUnsignedIntField", _ctype="unsigned int",
                                      bases=(NativeStructField, UnsignedIntField))

NativeLongField = _factory("NativeLongField", format="l", _ctype="long", bases=(NativeStructField, ))
NativeUnsignedLongField = _factory("NativeUnsignedLongField", format="L", _ctype="unsigned long",
                                   bases=(NativeStructField, ))

LongField = _factory("LongField", format="q", _ctype="int64_t", bases=(StructField,))
LELongField = _factory("LELongField", bases=(LittleEndianStructField, LongField))
BELongField = _factory("BELongField", bases=(BigEndianStructField, LongField))
StandardLongField = _factory("StandardLongField", bases=(StandardStructField, LongField))
NativeLongLongField = _factory("NativeLongLongField", _ctype="long long", ases=(NativeStructField, LongField))

UnsignedLongField = _factory("UnsignedLongField", format="Q", _ctype="uint64_t", bases=(StructField,))
LEUnsignedLongField = _factory("LEUnsignedLongField", bases=(LittleEndianStructField, UnsignedLongField))
BEUnsignedLongField = _factory("BEUnsignedLongField", bases=(BigEndianStructField, UnsignedLongField))
StandardUnsignedLongField = _factory("StandardUnsignedLongField", bases=(StandardStructField, UnsignedLongField))
NativeUnsignedLongLongField = _factory("NativeUnsignedLongLongField", _ctype="unsigned long long",
                                       bases=(NativeStructField, UnsignedLongField))

HalfPrecisionFloatField = _factory("HalfPrecisionFloatField", format="e", _ctype="binary16",
                                   bases=(StructField,))
LEHalfPrecisionFloatField = _factory("LEHalfPrecisionFloatField",
                                     bases=(LittleEndianStructField, HalfPrecisionFloatField))
BEHalfPrecisionFloatField = _factory("BEHalfPrecisionFloatField",
                                     bases=(BigEndianStructField, HalfPrecisionFloatField))
StandardHalfPrecisionFloatField = _factory("StandardHalfPrecisionFloatField",
                                           bases=(StandardStructField, HalfPrecisionFloatField))
NativeHalfPrecisionFloatField = _factory("NativeHalfPrecisionFloatField",
                                         bases=(NativeStructField, HalfPrecisionFloatField))

FloatField = _factory("FloatField", format="f", _ctype="float", bases=(StructField,))
LEFloatField = _factory("LEFloatField", bases=(LittleEndianStructField, FloatField))
BEFloatField = _factory("BEFloatField", bases=(BigEndianStructField, FloatField))
StandardFloatField = _factory("StandardFloatField", bases=(StandardStructField, FloatField))
NativeFloatField = _factory("NativeFloatField", bases=(NativeStructField, FloatField))

DoubleField = _factory("DoubleField", format="d", _ctype="double", bases=(StructField,))
LEDoubleField = _factory("LEDoubleField", bases=(LittleEndianStructField, DoubleField))
BEDoubleField = _factory("BEDoubleField", bases=(BigEndianStructField, DoubleField))
StandardDoubleField = _factory("StandardDoubleField", bases=(StandardStructField, DoubleField))
NativeDoubleField = _factory("NativeDoubleField", bases=(NativeStructField, DoubleField))
