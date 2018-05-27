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

Basic fields
============
.. autoclass:: FixedLengthField

   .. attribute:: FixedLengthField.length

       This specifies the length of the field. This is the amount of data that is read from the stream. It does not
       affect the amount of data that is written, however.

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

.. autoclass:: BitField

   When using the :class:`BitField`, you must be careful to align the bits to whole bytes. You can use multiple
   :class:`BitField`s consecutively without any problem, but the following would raise errors::

       class MultipleBitFields(Structure):
           bit0 = BitField(length=1)
           bit1 = BitField(length=1)
           byte = FixedLengthField(length=1)

   You can fix this by ensuring all consecutive bit fields align to a byte in total, or, alternatively, you can specify
   :attr:`realign` on the last :class:`BitField` to realign to the next byte:

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

.. autoclass:: TerminatedField

   .. attribute:: TerminatedField.terminator

      The terminator to read until. It can be multiple bytes. Defaults to a null-byte (``b'\0'``).

   Example usage::

       >>> class TerminatedStructure(Structure):
       ...     foo = TerminatedField()
       ...     bar = TerminatedField(terminator=b'\r\n')
       ...
       >>> TerminatedStructure.from_bytes(b"hello\0world\r\n")
       <TerminatedStructure: TerminatedStructure(foo=b'hello', bar=b'world')>

Common fields
=============

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


.. autoclass:: ArrayField

   .. attribute:: ArrayField.base_field

      The field that is to be repeated.

   .. attribute:: ArrayField.size

      This specifies the amount of repetitions of the base field.

      You can set it to one of the following:

      * A callable with zero arguments
      * A callable taking a :class:`ParsingContext` object
      * A string that represents the field name that contains the size
      * An integer

      The size given a context is obtained by calling ``ArrayField.get_size(value, context)``.

   Example usage::

       >>> class ArrayStructure(Structure):
       ...     count = UnsignedByteField()
       ...     foo = ArrayField(TerminatedField(terminator=b'\0'), size='count')
       ...
       >>> s = ArrayStructure.from_bytes(b"\x02hello\0world\0")
       >>> s.foo
       [b'hello', b'world']

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

