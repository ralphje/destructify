import struct

from . import FixedLengthField, NOT_PROVIDED


class StructField(FixedLengthField):
    format = None

    def __init__(self, format=NOT_PROVIDED, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if format is not NOT_PROVIDED:
            self.format = format
        self._struct = struct.Struct(self.format)
        self.length = self._struct.size

    def from_bytes(self, value):
        return self._struct.unpack(value)[0]

    def to_bytes(self, value):
        if value is None:
            value = 0
        return self._struct.pack(value)


def _factory(name, bases=(StructField, ), **kwargs):
    return type(name, bases, kwargs)


class AlignedStructField(StructField):
    _prefix = ""

    def __init__(self, *args, **kwargs):
        if self.format[0] in "@=<>!":
            self.format = self.format[1:]
        self.format = self._prefix + self.format
        super().__init__(*args, **kwargs)


LittleEndianStructField = _factory("LittleEndianStructField", _prefix="<", bases=(AlignedStructField, ))
BigEndianStructField = _factory("BigEndianStructField", _prefix=">", bases=(AlignedStructField, ))
StandardStructField = _factory("StandardStructField", _prefix="=", bases=(AlignedStructField, ))
NativeStructField = _factory("NativeStructField", _prefix="@", bases=(AlignedStructField, ))

CharField = _factory("CharField", format="c", ctype="char", bases=(StandardStructField,))
NativeCharField = _factory("NativeCharField", ctype="char", bases=(NativeStructField, CharField))

ByteField = _factory("ByteField", format="b", ctype="int8_t", bases=(StandardStructField,))
NativeByteField = _factory("SignedByteField", ctype="signed char", bases=(NativeStructField, ByteField))

UnsignedByteField = _factory("SignedByteField", format="B", ctype="uint8_t", bases=(StandardStructField,))
NativeUnsignedByteField = _factory("NativeSignedByteField", ctype="unsigned char",
                                   bases=(NativeStructField, UnsignedByteField))

BoolField = _factory("BoolField", format="?", ctype="_Bool", bases=(StandardStructField,))
NativeBoolField = _factory("NativeBoolField", bases=(NativeStructField, BoolField))

ShortField = _factory("ShortField", format="h", ctype="int16_t", bases=(StandardStructField,))
LEShortField = _factory("LEShortField", bases=(LittleEndianStructField, ShortField))
BEShortField = _factory("BEShortField", bases=(BigEndianStructField, ShortField))
NativeShortField = _factory("NativeShortField", ctype="short", bases=(NativeStructField, ShortField))

UnsignedShortField = _factory("UnsignedShortField", format="H", ctype="uint16_t", bases=(StandardStructField,))
LEUnsignedShortField = _factory("LEUnsignedShortField", bases=(LittleEndianStructField, UnsignedShortField))
BEUnsignedShortField = _factory("BEUnsignedShortField", bases=(BigEndianStructField, UnsignedShortField))
NativeUnsignedShortField = _factory("NativeUnsignedShortField", ctype="unsigned short",
                                    bases=(NativeStructField, UnsignedShortField))

IntegerField = _factory("IntegerField", format="i", ctype="int32_t", bases=(StandardStructField,))
LEIntegerField = _factory("LEIntegerField", bases=(LittleEndianStructField, IntegerField))
BEIntegerField = _factory("BEIntegerField", bases=(BigEndianStructField, IntegerField))
NativeIntegerField = _factory("NativeIntegerField", ctype="int", bases=(NativeStructField, IntegerField))

UnsignedIntegerField = _factory("UnsignedIntegerField", format="I", ctype="uint32_t", bases=(StandardStructField,))
LEUnsignedIntegerField = _factory("LEUnsignedIntegerField", bases=(LittleEndianStructField, UnsignedIntegerField))
BEUnsignedIntegerField = _factory("BEUnsignedIntegerField", bases=(BigEndianStructField, UnsignedIntegerField))
NativeUnsignedIntegerField = _factory("NativeUnsignedIntegerField", ctype="unsigned int",
                                      bases=(NativeStructField, UnsignedIntegerField))

NativeLongField = _factory("NativeLongField", format="l", ctype="long", bases=(NativeStructField, ))
NativeUnsignedLongField = _factory("NativeUnsignedLongField", format="L", ctype="unsigned long",
                                   bases=(NativeStructField, ))

LongField = _factory("LongField", format="q", ctype="int64_t", bases=(StandardStructField,))
LELongField = _factory("LELongField", bases=(LittleEndianStructField, LongField))
BELongField = _factory("BELongField", bases=(BigEndianStructField, LongField))
NativeLongLongField = _factory("NativeLongLongField", ctype="long long", ases=(NativeStructField, LongField))

UnsignedLongField = _factory("UnsignedLongField", format="Q", ctype="uint64_t", bases=(StandardStructField,))
LEUnsignedLongField = _factory("LEUnsignedLongField", bases=(LittleEndianStructField, UnsignedLongField))
BEUnsignedLongField = _factory("BEUnsignedLongField", bases=(BigEndianStructField, UnsignedLongField))
NativeUnsignedLongLongField = _factory("NativeUnsignedLongLongField", ctype="unsigned long long",
                                       bases=(NativeStructField, UnsignedLongField))

HalfPrecisionFloatField = _factory("HalfPrecisionFloatField", format="e", ctype="binary16",
                                   bases=(StandardStructField,))
LEHalfPrecisionFloatField = _factory("LEHalfPrecisionFloatField",
                                     bases=(LittleEndianStructField, HalfPrecisionFloatField))
BEHalfPrecisionFloatField = _factory("BEHalfPrecisionFloatField",
                                     bases=(BigEndianStructField, HalfPrecisionFloatField))
NativeHalfPrecisionFloatField = _factory("NativeHalfPrecisionFloatField",
                                         bases=(NativeStructField, HalfPrecisionFloatField))

FloatField = _factory("FloatField", format="f", ctype="float", bases=(StandardStructField,))
LEFloatField = _factory("LEFloatField", bases=(LittleEndianStructField, FloatField))
BEFloatField = _factory("BEFloatField", bases=(BigEndianStructField, FloatField))
NativeFloatField = _factory("NativeFloatField", bases=(NativeStructField, FloatField))

DoubleField = _factory("DoubleField", format="d", ctype="double", bases=(StandardStructField,))
LEDoubleField = _factory("LEDoubleField", bases=(LittleEndianStructField, DoubleField))
BEDoubleField = _factory("BEDoubleField", bases=(BigEndianStructField, DoubleField))
NativeDoubleField = _factory("NativeDoubleField", bases=(NativeStructField, DoubleField))
