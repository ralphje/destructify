======
Fields
======
.. module:: destructify

As part of the definition of a :class:`Structure`, fields are used to interpret and write a small part of a binary
structure. Each field is responsible for the following:

* How to consume precisely enough bytes from a stream of bytes
* How to convert these bytes to a Python representation
* How to convert this back to a bytes representation
* How to write this back to a stream of bytes

.. _StringFieldExample:

Controlling through attributes
==============================
It is not possible to make a general assumption about all fields, but most fields combine different methods of consuming
and writing data to and from a stream, with a single Python representation. Taking the :class:`StringField` as an
example, you may have noticed that we are only able to fit 5-byte names in this field. What if we had longer or shorter
names? Luckily, :class:`StringField` allows you to pass different keyword-arguments to define how this works:

``StringField(length=5)``
  We have teen this before, this allows us to read precisely five bytes and interpret this as a str.

``StringField(length=20, padding=b' ')``
  This still reads 20 bytes from the field, but discards all spaces from the right as being padding. This allows us to
  write names with up to 20 characters in width, and fill the rest with spaces.

``StringField(terminator=b'\0')``
  This is a totally different method of writing a name. This reads the name until it encounters a NULL-byte. This is
  typically how strings are represented in C, and are called NULL-terminated strings. The advantage of this is that the
  name can be anywhere from zero to infinity bytes long, as long as it is terminated with a NULL-byte (and the name
  itself does not contain any NULL-bytes, which is unlikely).

``StringField(length=20, terminator=b'\0')``
  This combines the above two methods: first 20 bytes are read from the stream, and then everything after the first
  NULL-byte is discarded. This is different from defining length with padding, as defining a terminator will allow
  Destructify to work from left to right and stop at the first occurence of the terminator, while the padding method
  will require it to work from right to left and stop just before the first other character. Another difference is that
  this field must contain precisely 20 characters when writing, as we have not defined how to pad the remaining
  length if we have insufficient bytes.

``StringField(length=20, terminator=b'\0', padding=b'\0')``
  This is the best of all worlds, allowing us to read 20 bytes, terminate the relevant part at the NULL-terminator while
  reading, and allow us to write shorter-length values as these will be padded with NULL-bytes. This is usually how
  you'd implement fixed-length C-style strings.

As you can see from these five examples, it highly depends on how your structure looks like what you'd define in the
structure. Again, these are only examples, and you should read :ref:`FieldSpec` to get an idea of all of the options
for all of the built-in fields.

Field idempotency
=================
To ensure consistency across all fields, the following holds true for all built-in fields and custom fields should
attempt to adhere to these as well:

    When a value, that is written by a field, is read and written again by that same field, the byte representation
    must be the same.

    When a value, that is read by a field, is written and read again by that same field, the Python representation
    must be the same.

We call these two truths the *idempotency of a field*. In the most common case, this means that a byte and Python
representation must be directly linked to each other. For instance, ``b'foo' == b'foo'`` holds true for a
:class:`ByteField`, and no other representation maps to the same byte sequence or Python representation. This is
called *simple idempotency*, and asserts that hte two truths are always true.

In some cases, this does not hold. This is the case when different inputs converge to the same representation.

For instance, when we consider a :class:`VariableLengthQuantityField`, the byte
representation of a value may be prepended with ``80`` bytes and they do not change the value of the field. So, when
some other writer writes these pointless bytes, Destructify has to ignore them. When writing a value, Destructify will
then opt to write the least amount of bytes possible, meaning that the byte representation differs from the value that
was read. However, Destructify can read this value again and it will be the same Python representation.

Similarly, a field may allow different types to be written to a stream. For instance, the :class:`EnumField` allows you
to write arbitrary values to :class:`Field.to_stream`, but will always read them as :class:`enum.Enum`, and also allows
you to write this :class:`enum.Enum` back to the stream.

All built-in fields will ensure that the two truths hold. If this is not possible, for instance due to alignment issues,
an error will be raised. Some fields allow you to specify ``strict=False``, which will disable these checks and may
break idempotency.

Writing a custom field
======================
Although there are many built-in fields, you may occasionally run into some field structure that has not been defined
yet in Destructify. Luckily, it is very easy to write your own field specification.

Subclassing an existing field
-----------------------------
If you only need to change a field a little bit, you may be best off subclassing an existing field and changing how
it behaves. Say, for instance, we have a field that follows normal parsing rules for bytes, but requires us to read
the result from back-to-front. We could simply subclass :class:`BytesField` and change this. Since subclassing
:class:`BytesField` is a common occurrence, it even provides a simple hook to do this::

    class ReversedBytesField(BytesField):
        def to_python(value):
            return value[::-1]
        def from_python(value):
            return value[::-1]

We omitted the ``super()``-call for brevity and since we know these functions are simple hooks of :class:`BytesField`.
If we wanted to subclass :class:`IntegerField` to return an IPAddress object instead, we should have done this::

    import ipaddress
    class IPAddressField(IntegerField):
        def __init__(self, *args, length=4, signed=False, **kwargs):
            super().__init__(*args, length=length, signed=signed, **kwargs)
        def to_python(value):
            return ipaddress.IPAddress(super().to_python(value))
        def from_python(value):
            return super().from_python(int(value))

You can similarly extend the behaviour of any other existing class using standard Python inheritance.

Writing your own field
----------------------
However, what
if none of the fields does what you want? Then you have to create a class inheriting from :class:`Field` and override
:meth:`Field.from_stream` and :meth:`Field.to_stream`.

Take, for instance, `variable-length quantities <https://en.wikipedia.org/wiki/Variable-length_quantity>`_. Since this
had to be written for this documentation anyway, it is included in Destuctify, but assume we hadn't. Then you'd write
it as follows::

    class VariableLengthQuantityField(Field):
        def from_stream(self, stream, context):
            result = count = 0
            while True:
                count += 1
                c = context.read_stream(stream, 1)[0]  # TODO: verify that 1 byte is read
                result <<= 7
                result += c & 0x7f
                if not c & 0x80:
                    break
            return result, count

        def to_stream(self, stream, value, context):  # TODO: check that value is positive
            result = [value & 0x7f]
            value >>= 7
            while value > 0:
                result.insert(0, value & 0x7f | 0x80)
                value >>= 7
            return context.write_stream(stream, bytes(result))

As you can see, this is not that hard! We have omitted some additional checks from this example, such as that we
have actually read 1 byte (and should raise :exc:`StreamExhaustedError` if it isn't) and verify that the value is
positive when writing, but other than that, this field should work.

In this case it is easily accomplished, but you must always make sure that the stream cursor is at the correct position
after the :meth:`Field.to_stream` and :meth:`Field.from_stream` methods are done. Typically, this will hold::

    tell_before = stream.tell()
    result = Field.to_stream(stream, ...)   # similar for from_stream
    tell_before + result == stream.tell()

Testing your field
------------------
Now, the only thing left is writing unittests for this. Since this field is mostly simple idempotent, we can use these
simple tests to verify it all works according to plan, You may notice that the only simple idempotency exception is
that values may be repended with ``80`` bytes as that does not change its value::

    class VariableLengthQuantityFieldTest(DestructifyTestCase):
        def test_basic(self):
            self.assertFieldStreamEqual(b'\x00', 0x00, VariableLengthQuantityField())
            self.assertFieldStreamEqual(b'\x7f', 0x7f, VariableLengthQuantityField())
            self.assertFieldStreamEqual(b'\x81\x00', 0x80, VariableLengthQuantityField())
            self.assertFieldFromStreamEqual(b'\x80\x80\x7f', 0x7f, VariableLengthQuantityField())

        def test_negative_value(self):
            with self.assertRaises(OverflowError):
                self.call_field_to_stream(VariableLengthQuantityField(), -1)

        def test_stream_not_sufficient(self):
            with self.assertRaises(StreamExhaustedError):
                self.call_field_from_stream(VariableLengthQuantityField(), b'\x81\x80\x80')

Parsing context
===============

.. class:: ParsingContext

   While parsing, it is important to have some context; some fields depend on other fields during writing and during
   reading. The :class:`ParsingContext` object is passed to several methods for this.

   When using this module, you will get a :class:`ParsingContext` when you define a property of a field that depends
   on another field. This is handled by storing all previously parsed fields in the context, or (if applicable) the
   :class:`Structure` the field is part of. You can access this as follows::

       context['field_name']

   But, as a shorthand, you can also access it as an attribute of the :attr:`f` object::

       context.f.field_name


   .. describe:: context[key]

      Returns the value of the specified *key*, either from the already parsed fields, or from the underlying structure,
      depending on the situation.

   .. attribute:: ParsingContext.f

      This object is typically used in ``lambda`` closures in :class:`Field` declarations.

      The :attr:`f` attribute allows you to access fields from this context, using attribute access. This is similar to
      using ``context[key]``, but provides a little bit cleaner syntax. This object is separated from the scope of
      :attr:`ParsingContext` to avoid any name collisions with field names. (For instance, a field named ``f`` would
      be impossible to reach otherwise).

      .. describe:: f.name

         Access the current value of the named field in the :class:`ParsingContext`, equivalent to
         ``ParsingContext[name]``

      .. describe:: f[name]

         Alias for attribute access to allow accessing names that are dynamic or collide with the namespace (see below)

      Two attributes are offered for parent and root access, and a third one to access the :class:`ParsingContext`.
      These names still collide with field names you may want to specify, but the ``f``-object is guaranteed to not add
      any additional name collisions in minor releases.

      .. attribute:: ParsingContext.f._

         Returns the :attr:`ParsingContext.f` attribute of the :attr:`ParsingContext.parent` object, so you can write
         ``f.parent.parent.field``, which is equivalent to ``context.parent.parent['field']``.

         If you need to access a field named ``_``, you must use ``f['_']``

      .. attribute:: ParsingContext.f._root

         Returns the :attr:`ParsingContext.f` attribute of the :attr:`ParsingContext.root` object, so you can write
         ``f.root.field``, which is equivalent to ``context.root['field']``

         If you need to access a field named ``_root``, you must use ``f['_root']``

      .. attribute:: ParsingContext.f._context

         Returns the actual :class:`ParsingContext`. Used in cases where a :attr:`f`-object is only provided.

         If you need to access a field named ``_context``, you must use ``f['_context']``

   .. attribute:: ParsingContext.parent

      Access to the parent context (useful when parsing a Structure inside a Structure). May be :const:`None` if this is
      the uppermost context.

   .. autoattribute:: ParsingContext.root

   .. attribute:: ParsingContext.fields

      This is a dictionary of names to information about parsed fields. You can use this to access information of how
      the fields were parsed. This is typically for debugging purposes, or displaying information about parsing
      structures.

   .. autoattribute:: ParsingContext.field_values

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

   .. autoattribute:: Field.ctype

   A :class:`Field` also defines the following methods:

   .. describe:: len(field)

      You can call ``len`` on a field to retrieve its byte length. It can either return a value that makes sense, or it
      will raise an :exc:`ImpossibleToCalculateLengthError` when the length depends on something that is not known yet.

   .. automethod:: Field.initialize

   .. automethod:: Field.get_final_value

   .. automethod:: Field.from_stream

   .. automethod:: Field.to_stream
