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
NativeCharField = _factory("NativeCharField", ctype="char", bases=(CharField, NativeStructField))

ByteField = _factory("ByteField", format="b", ctype="int8_t", bases=(StandardStructField,))
NativeByteField = _factory("SignedByteField", ctype="signed char", bases=(ByteField, NativeStructField))

UnsignedByteField = _factory("SignedByteField", format="B", ctype="uint8_t", bases=(StandardStructField,))
NativeUnsignedByteField = _factory("NativeSignedByteField", ctype="unsigned char",
                                   bases=(UnsignedByteField, NativeStructField))

BoolField = _factory("BoolField", format="?", ctype="_Bool", bases=(StandardStructField,))
NativeBoolField = _factory("NativeBoolField", bases=(BoolField, NativeStructField))

ShortField = _factory("ShortField", format="h", ctype="int16_t", bases=(StandardStructField,))
LEShortField = _factory("LEShortField", bases=(ShortField, LittleEndianStructField))
BEShortField = _factory("BEShortField", bases=(ShortField, BigEndianStructField))
NativeShortField = _factory("NativeShortField", ctype="short", bases=(ShortField, NativeStructField))

UnsignedShortField = _factory("UnsignedShortField", format="H", ctype="uint16_t", bases=(StandardStructField,))
LEUnsignedShortField = _factory("LEUnsignedShortField", bases=(UnsignedShortField, LittleEndianStructField))
BEUnsignedShortField = _factory("BEUnsignedShortField", bases=(UnsignedShortField, BigEndianStructField))
NativeUnsignedShortField = _factory("NativeUnsignedShortField", ctype="unsigned short",
                                    bases=(UnsignedShortField, NativeStructField))

IntegerField = _factory("IntegerField", format="i", ctype="int32_t", bases=(StandardStructField,))
LEIntegerField = _factory("LEIntegerField", bases=(IntegerField, LittleEndianStructField))
BEIntegerField = _factory("BEIntegerField", bases=(IntegerField, BigEndianStructField))
NativeIntegerField = _factory("NativeIntegerField", ctype="int", bases=(IntegerField, NativeStructField))

UnsignedIntegerField = _factory("UnsignedIntegerField", format="I", ctype="uint32_t", bases=(StandardStructField,))
LEUnsignedIntegerField = _factory("LEUnsignedIntegerField", bases=(UnsignedIntegerField, LittleEndianStructField))
BEUnsignedIntegerField = _factory("BEUnsignedIntegerField", bases=(UnsignedIntegerField, BigEndianStructField))
NativeUnsignedIntegerField = _factory("NativeUnsignedIntegerField", ctype="unsigned int",
                                      bases=(UnsignedIntegerField, NativeStructField))

NativeLongField = _factory("NativeLongField", format="l", ctype="long", bases=(NativeStructField, ))
NativeUnsignedLongField = _factory("NativeUnsignedLongField", format="L", ctype="unsigned long",
                                   bases=(NativeStructField, ))

LongIntegerField = _factory("LongIntegerField", format="q", ctype="int64_t", bases=(StandardStructField,))
LELongIntegerField = _factory("LELongIntegerField", bases=(LongIntegerField, LittleEndianStructField))
BELongIntegerField = _factory("BELongIntegerField", bases=(LongIntegerField, BigEndianStructField))
NativeLongLongIntegerField = _factory("NativeLongLongIntegerField", ctype="long long",
                                      bases=(LongIntegerField, NativeStructField))

UnsignedLongIntegerField = _factory("UnsignedLongIntegerField", format="Q", ctype="uint64_t",
                                    bases=(StandardStructField,))
LEUnsignedLongIntegerField = _factory("LEUnsignedLongIntegerField",
                                      bases=(UnsignedLongIntegerField, LittleEndianStructField))
BEUnsignedLongIntegerField = _factory("BEUnsignedLongIntegerField",
                                      bases=(UnsignedLongIntegerField, BigEndianStructField))
NativeUnsignedLongLongIntegerField = _factory("NativeUnsignedLongLongIntegerField", ctype="unsigned long long",
                                              bases=(UnsignedLongIntegerField, NativeStructField))

HalfPrecisionFloatField = _factory("HalfPrecisionFloatField", format="e", ctype="binary16",
                                   bases=(StandardStructField,))
LEHalfPrecisionFloatField = _factory("LEHalfPrecisionFloatField",
                                     bases=(HalfPrecisionFloatField, LittleEndianStructField))
BEHalfPrecisionFloatField = _factory("BEHalfPrecisionFloatField",
                                     bases=(HalfPrecisionFloatField, BigEndianStructField))
NativeHalfPrecisionFloatField = _factory("NativeHalfPrecisionFloatField",
                                         bases=(HalfPrecisionFloatField, NativeStructField))

FloatField = _factory("FloatField", format="f", ctype="float", bases=(StandardStructField,))
LEFloatField = _factory("LEFloatField", bases=(FloatField, LittleEndianStructField))
BEFloatField = _factory("BEFloatField", bases=(FloatField, BigEndianStructField))
NativeFloatField = _factory("NativeFloatField", bases=(FloatField, NativeStructField))

DoubleField = _factory("FloatField", format="d", ctype="double", bases=(StandardStructField,))
LEDoubleField = _factory("LEFloatField", bases=(DoubleField, LittleEndianStructField))
BEDoubleField = _factory("BEFloatField", bases=(DoubleField, BigEndianStructField))
NativeDoubleField = _factory("NativeFloatField", bases=(DoubleField, NativeStructField))

