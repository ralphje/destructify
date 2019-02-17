======
Fields
======
.. module:: destructify.fields

A field is part of the specification of a Structure. Fields can be very simple: only defining how to convert a
:const:`bytes` value to a Python representation and vice-versa. They can be much more complicated, however.

Parsing context
===============

.. class:: ParsingContext

   While parsing, it is important to have some context; some fields depend on other fields during writing and during
   reading. The :class:`ParsingContext` object is passed to several methods for this.

   When using this module, you will get a :class:`ParsingContext` when you define a property of a field that depends
   on another field. This is handled by storing all previously parsed fields in the context, or (if applicable) the
   :class:`Structure` the field is part of. You can access this as follows::

       context['field_name']

   But, as a shorthand, you can also access it as an attribute::

       context.field_name

   When you are implementing a field yourself, you get a :class:`ParsingContext` when reading from and writing to a
   stream, meaning you will probably use one the following methods:

   .. automethod:: ParsingContext.read_stream

   .. automethod:: ParsingContext.write_stream

   .. automethod:: ParsingContext.finalize_stream

   .. automethod:: ParsingContext.read_stream_bits

   .. automethod:: ParsingContext.write_stream_bits

Base field
==========
.. autoclass:: Field

   The base field does provide some common attributes and methods:

   .. attribute:: Field.name

      The field name. This is set automatically by the :class:`Structure`'s metaclass when it is initialized.

   .. attribute:: Field.default

       The field's default value. This is used when the :class:`Structure` is initialized if it is provided. If it is not
       provided, the field determines its own default value.

       You can set it to one of the following:

       * A callable with zero arguments
       * A callable taking a :class:`ParsingContext` object
       * A value

       All of the following are valid usages of the default attribute::

           Field(default=None)
           Field(default=3)
           Field(default=lambda: datetime.datetime.now())
           Field(default=lambda c: c.value)

       You can check whether a default is set using the :attr:`Field.has_default` attribute. The default given a context is
       obtained by calling ``Field.get_default(context)``

   .. attribute:: Field.override

       Using :attr:`Field.override`, you can change the value of the field in a structure, just before it is being written to a
       stream. This is useful if you, for instance, wish to override a field's value based on some other property in the
       structure. For instance, you can change a length field based on the actual length of a field.

       You can set it to one of the following:

       * A value
       * A callable taking a :class:`ParsingContext` object and the current value of the field

       For instance::

           Field(override=3)
           Field(override=lambda c, v: c.value if v is None else v)

       You can check whether an override is set using the :attr:`Field.has_override` attribute. The override given a context is
       obtained by calling ``Field.get_overridden_value(value, context)``. Note, however, that you probably want to call
       :meth:`Field.get_final_value` instead.

   .. autoattribute:: Field.ctype

   A :class:`Field` also defines the following methods:

   .. automethod:: Field.__len__

   .. automethod:: Field.initialize

   .. automethod:: Field.get_final_value

   .. automethod:: Field.from_stream

   .. automethod:: Field.from_bytes

   .. automethod:: Field.to_stream

   .. automethod:: Field.to_bytes

Byte fields
===========
FixedLengthField
----------------
.. autoclass:: FixedLengthField

   .. attribute:: FixedLengthField.length

      This specifies the length of the field. This is the amount of data that is read from the stream and written to
      the stream.

      You can set it to one of the following:

      * A callable with zero arguments
      * A callable taking a :class:`ParsingContext` object
      * A string that represents the field name that contains the length
      * An integer

      For instance::

          class StructureWithLength(Structure):
              length = UnsignedByteField()
              value = FixedLengthField(length='length')

      The length given a context is obtained by calling ``FixedLengthField.get_length(value, context)``.

   When the class is initialized on a :class:`Structure`, and the length property is specified using a string, the
   default implementation of the :attr:`Field.override` on the named attribute of the :class:`Structure` is changed
   to match the length of the value in this :class:`Field`.

   Continuing the above example, the following works automatically::

       >>> bytes(StructureWithLength(value=b"123456"))
       b'\x06123456'

   However, explicitly specifying the length would override this::

       >>> bytes(StructureWithLength(length=1, value=b"123456"))
       b'\x01123456'

   This behaviour can be changed by manually specifying a different :attr:`Field.override` on ``length``.

   .. attribute:: FixedLengthField.strict

      This boolean (defaults to :const:`True`) enables raising errors in the following cases:

      * A :class:`StreamExhaustedError` when there are not sufficient bytes to completely fill the field while reading.
      * A :class:`WriteError` when there are not sufficient bytes to fill the field while writing and
        :attr:`padding` is not set.
      * A :class:`WriteError` when the field must be padded, but the bytes that are to be written are not a multiple of
        the size of :attr:`padding`.
      * A :class:`WriteError` when there are too many bytes to fit in the field while writing.

      Disabling :attr:`FixedLengthField.strict` is not recommended, as this may cause inadvertent errors.

   .. attribute:: FixedLengthField.padding

      When set, this value is used to pad the bytes to fill the entire field while writing, and chop this off the
      value while reading. Padding is removed right to left and must be aligned to the end of the value (which matters
      for multibyte paddings).

      While writing in :attr:`strict` mode, and the remaining bytes are not a multiple of the length of this value,
      a :class:`WriteError` is raised. If :attr:`strict` mode is not enabled, the padding will simply be appended to the
      value and chopped of whenever required. However, this can't be parsed back by Destructify (as the padding is not
      aligned to the end of the structure).

TerminatedField
---------------

.. autoclass:: TerminatedField

   .. attribute:: TerminatedField.terminator

      The terminator to read until. It can be multiple bytes. Defaults to a null-byte (``b'\0'``).

   .. attribute:: TerminatedField.step

      The size of the steps for finding the terminator. This is useful if you have a multi-byte terminator that is
      aligned. For instance, when reading NULL-terminated UTF-16 strings, you'd expect two NULL bytes aligned to two
      bytes. Defaults to 1.

   Example usage::

       >>> class TerminatedStructure(Structure):
       ...     foo = TerminatedField()
       ...     bar = TerminatedField(terminator=b'\r\n')
       ...
       >>> TerminatedStructure.from_bytes(b"hello\0world\r\n")
       <TerminatedStructure: TerminatedStructure(foo=b'hello', bar=b'world')>

String fields
=============
There are two flavours of string fields: the :class:`FixedLengthStringField` is used for strings that are contained in
fixed-length fields, and is a subclass of :class:`FixedLengthField`, and the :class:`TerminatedStringField` that is used
for terminated strings, using :class:`TerminatedField` as base.

Both string fields have the following attributes:

.. autoclass:: StringFieldMixin

   .. attribute:: StringFieldMixin.encoding

      The encoding of the string. Defaults to ``utf-8``, but can be any encoding supported by Python.

   .. attribute:: StringFieldMixin.errors

      The error handler for encoding/decoding failures. Defaults to Python's default of ``strict``.

.. autoclass:: FixedLengthStringField

   See :class:`FixedLengthField` and :class:`StringFieldMixin` for all attributes.

.. autoclass:: TerminatedStringField

   See :class:`TerminatedField` and :class:`StringFieldMixin` for all attributes.

Numeric fields
==============

IntegerField
------------

.. note::
   The :class:`IntegerField` is not to be confused with the :class:`IntField`, which is based on :class:`StructField`.
   For readability, you are recommended to use the :class:`IntegerField` whenever possible.

.. autoclass:: IntegerField


   .. attribute:: IntegerField.length

      The length (in bytes) of the field. When writing a number that is too large to be held in this field, you will
      get an ``OverflowError``.

   .. attribute:: IntegerField.byte_order

      The byte order (i.e. endianness) of the bytes in this field. If you do not specify this, you must specify a
      ``byte_order`` on the structure.

   .. attribute:: IntegerField.signed

      Boolean indicating whether the integer is to be interpreted as a signed or unsigned integer.

BitField
--------

.. autoclass:: BitField

   When using the :class:`BitField`, you must be careful to align the bits to whole bytes. You can use multiple
   :class:`BitField` s consecutively without any problem, but the following would raise errors::

       class MultipleBitFields(Structure):
           bit0 = BitField(length=1)
           bit1 = BitField(length=1)
           byte = FixedLengthField(length=1)

   You can fix this by ensuring all consecutive bit fields align to a byte in total, or, alternatively, you can specify
   :attr:`realign` on the last :class:`BitField` to realign to the next byte.

   .. attribute:: BitField.realign

      This specifies whether the stream must be realigned to entire bytes after this field. If set, after bits have
      been read, bits are skipped until the next whole byte. This means that the intermediate bits are ignored. When
      writing and this boolean is set, it is padded with zero-bits until the next byte boundary.

      Note that this means that the following::

           class BitStructure(Structure):
               foo = BitField(length=5, realign=True)
               bar = FixedLengthField(length=1)

      Results in this parsing structure::

           76543210  76543210
           fffff     bbbbbbbb

      Thus, ignoring bits 2-0 from the first byte.

Struct fields
=============
Destructify allows you to use 'classic' :mod:`struct` constructs as well.

StructField
-----------

.. autoclass:: StructField

   .. attribute:: StructField.format

      The format to be passed to the struct module. See
      `Struct Format Strings`<https://docs.python.org/3/library/struct.html#format-strings> in the manual of Python
      for information on how to construct these.

      You do not need to include the byte order. If you do, it acts as a default for the byte_order attribute, although
      that takes precedence.

   .. attribute:: StructField.byte_order

      The byte order to use for the struct. If this is not specified, an none is provided in the :attr:`format` field,
      it defaults to the ``byte_order`` specified in the meta of the Structure.

Subclasses of StructField
-------------------------

This project also provides a smorgasbord of several default implementations for the different types of structs. First
off, there are four different kinds of base classes for the different byte orders:

=============  ======  ================================
Byte order     Format  Class name
=============  ======  ================================
little endian  ``<``   :class:`LittleEndianStructField`
big endian     ``>``   :class:`BigEndianStructField`
standard       ``=``   :class:`StandardStructField`
native         ``@``   :class:`NativeStructField`
=============  ======  ================================

Each of the different formats supported by the struct module also gets a different base class. All of these are then
combined into a multiple-inheritance structure where each specific structure inherits both from one of the
byte-order classes above and one of the base classes. For instance, :class:`StandardShortField` inherits from both a
:class:`ShortField` and a :class:`StandardStructField`.

.. hint::
   Use a :class:`IntegerField` when you know the amount of bytes you need to parse. Classes below are typically used
   for system structures and the :class:`IntegerField` is typically used for network structures.

Each of the classes is listed in the table below.

+----------------------------------+--------+----------------------------------------------------------+
| Base class                       | Format | Classes                                                  |
+==================================+========+====================================+=====================+
| :class:`CharField`               | ``c``  | | **native**: :class:`NativeCharField`                   |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`ByteField`               | ``b``  | | **native**: :class:`NativeByteField`                   |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`UnsignedByteField`       | ``B``  | | **native**: :class:`NativeUnsignedByteField`           |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`BoolField`               | ``?``  | | **native**: :class:`NativeBoolField`                   |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`ShortField`              | ``h``  | | **little endian**: :class:`LEShortField`               |
|                                  |        | | **big endian**: :class:`BEShortField`                  |
|                                  |        | | **standard**: :class:`StandardShortField`              |
|                                  |        | | **native**: :class:`NativeShortField`                  |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`UnsignedShortField`      | ``H``  | | **little endian**: :class:`LEUnsignedShortField`       |
|                                  |        | | **big endian**: :class:`BEUnsignedShortField`          |
|                                  |        | | **standard**: :class:`StandardUnsignedShortField`      |
|                                  |        | | **native**: :class:`NativeUnsignedShortField`          |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`IntField`                | ``i``  | | **little endian**: :class:`LEIntField`                 |
|                                  |        | | **big endian**: :class:`BEIntField`                    |
|                                  |        | | **standard**: :class:`StandardIntField`                |
|                                  |        | | **native**: :class:`NativeIntField`                    |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`UnsignedIntField`        | ``I``  | | **little endian**: :class:`LEUnsignedIntField`         |
|                                  |        | | **big endian**: :class:`BEUnsignedIntField`            |
|                                  |        | | **standard**: :class:`StandardUnsignedIntField`        |
|                                  |        | | **native**: :class:`NativeUnsignedIntField`            |
+----------------------------------+--------+----------------------------------------------------------+
| n/a                              | ``l``  | | **native**: :class:`NativeLongField`                   |
+----------------------------------+--------+----------------------------------------------------------+
| n/a                              | ``L``  | | **native**: :class:`NativeUnsignedLongField`           |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`LongField`               | ``q``  | | **little endian**: :class:`LELongField`                |
|                                  |        | | **big endian**: :class:`BELongField`                   |
|                                  |        | | **standard**: :class:`StandardLongField`               |
|                                  |        | | **native**: :class:`NativeLongLongField`               |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`UnsignedLongField`       | ``Q``  | | **little endian**: :class:`LEUnsignedLongField`        |
|                                  |        | | **big endian**: :class:`LEUnsignedLongField`           |
|                                  |        | | **standard**: :class:`BEUnsignedLongField`             |
|                                  |        | | **native**: :class:`NativeUnsignedLongLongField`       |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`HalfPrecisionFloatField` | ``e``  | | **little endian**: :class:`LEHalfPrecisionFloatField`  |
|                                  |        | | **big endian**: :class:`BEHalfPrecisionFloatField`     |
|                                  |        | | **standard**: :class:`StandardHalfPrecisionFloatField` |
|                                  |        | | **native**: :class:`NativeHalfPrecisionFloatField`     |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`FloatField`              | ``f``  | | **little endian**: :class:`LEFloatField`               |
|                                  |        | | **big endian**: :class:`BEFloatField`                  |
|                                  |        | | **standard**: :class:`StandardFloatField`              |
|                                  |        | | **native**: :class:`NativeFloatField`                  |
+----------------------------------+--------+----------------------------------------------------------+
| :class:`DoubleField`             | ``d``  | | **little endian**: :class:`LEDoubleField`              |
|                                  |        | | **big endian**: :class:`BEDoubleField`                 |
|                                  |        | | **standard**: :class:`StandardDoubleField`             |
|                                  |        | | **native**: :class:`NativeDoubleField`                 |
+----------------------------------+--------+----------------------------------------------------------+

Other fields
============

StructureField
--------------

.. autoclass:: StructureField

   .. attribute:: StructureField.structure

      The :class:`Structure` class that is initialized for the sub-structure.

   Example usage::

       >>> class Sub(Structure):
       ...     foo = FixedLengthField(length=11)
       ...
       >>> class Encapsulating(Structure):
       ...     bar = StructureField(Sub)
       ...
       >>> s = Encapsulating.from_bytes(b"hello world")
       >>> s
       <Encapsulating: Encapsulating(bar=<Sub: Sub(foo=b'hello world')>)>
       >>> s.bar
       <Sub: Sub(foo=b'hello world')>
       >>> s.bar.foo
       b'hello world'


ArrayField
----------

.. autoclass:: ArrayField

   .. attribute:: ArrayField.base_field

      The field that is to be repeated.

   .. attribute:: ArrayField.count

      This specifies the amount of repetitions of the base field.

      You can set it to one of the following:

      * A callable with zero arguments
      * A callable taking a :class:`ParsingContext` object
      * A string that represents the field name that contains the size
      * An integer

      The count given a context is obtained by calling ``ArrayField.get_count(value, context)``.

   Example usage::

       >>> class ArrayStructure(Structure):
       ...     count = UnsignedByteField()
       ...     foo = ArrayField(TerminatedField(terminator=b'\0'), size='count')
       ...
       >>> s = ArrayStructure.from_bytes(b"\x02hello\0world\0")
       >>> s.foo
       [b'hello', b'world']

ConditionalField
----------------
.. autoclass:: ConditionalField

   .. attribute:: ConditionalField.base_field

      The field that is conditionally present.

   .. attribute:: ConditionalField.condition

      This specifies the condition on whether the field is present.

      You can set it to one of the following:

      * A callable with zero arguments
      * A callable taking a :class:`ParsingContext` object
      * A string that represents the field name that evaluates to true or false. Note that ``b'\0'`` evaluates to true.
      * A value that is to be evaluated

      The condition given a context is obtained by calling ``ConditionalField.get_condition(value, context)``.

EnumField
---------
.. autoclass:: EnumField

   .. attribute:: EnumField.base_field

      The field that returns the value that is provided to the :class:`enum.Enum`

   .. attribute:: EnumField.enum

      The :class:`enum.Enum` class.

   You can also use an :class:`EnumField` to handle flags::

       >>> class Permissions(enum.IntFlag):
       ...     R = 4
       ...     W = 2
       ...     X = 1
       ...
       >>> class EnumStructure(Structure):
       ...     perms = EnumField(UnsignedByteField(), enum=Permissions)
       ...
       >>> EnumStructure.from_bytes(b"\x05")
       <EnumStructure: EnumStructure(perms=<Permissions.R|X: 5>)>

