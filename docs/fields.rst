.. _CustomFields:

=============
Custom fields
=============
.. module:: destructify

As part of the definition of a :class:`Structure`, fields are used to interpret and write a small part of a binary
structure. Each field is responsible for the following:

* Finding the start of the field relative to the previous field
* Consuming precisely enough bytes from a stream of bytes
* Converting these bytes to a Python representation
* Converting this back to a bytes representation
* Writing this back to a stream of bytes

Field idempotency
=================
To ensure consistency across all fields, we have chosen to define two idempotency rules that holds for all built-in
fields. Custom fields should attempt to adhere to these as well:

.. admonition:: The idempotency of a field

   When a value, that is written by a field, is read and written again by that same field, the byte representation
   must be the same.

   When a value, that is read by a field, is written and read again by that same field, the Python representation
   must be the same.

What does it mean? In the most simple case, the byte and Python representation are linked to each other. This means,
for instance, that writing ``b'foo'`` to a :class:`BytesField`, will result in a ``b'foo'`` in the stream, and no other
value has the same property.

In some cases, this does not hold. This is the case when different inputs converge to the same representation.
For instance, considering a :class:`VariableLengthIntegerField`, the byte
representation of a value may be prepended with ``0x80`` bytes and they do not change the value of the field. So, when
some other writer writes these pointless bytes, Destructify has to ignore them. When writing a value, Destructify will
then opt to write the least amount of bytes possible, meaning that the byte representation differs from the value that
was read. However, Destructify can read this value again and it will be the same Python representation.

Similarly, a field may allow different types to be written to a stream. For instance, the :class:`EnumField` allows you
to write arbitrary values to :class:`Field.to_stream`, but will always read them as :class:`enum.Enum`, and also allows
you to write this :class:`enum.Enum` back to the stream.

All built-in fields will ensure that the two truths hold. If this is not possible, for instance due to alignment issues,
an error will be raised. Some fields allow you to specify ``strict=False``, which will disable these checks and may
break idempotency.

Subclassing an existing field
=============================
If you only need to modify a field a little bit, you can probably come by with decoding/encoding-pairs
(see :ref:`DecodingEncoding`).
Although these can be quite useful, they have one important limitation: you can't change the way the
field reads and returns its value. Additionally, if you have to continuously write the same decoding/encoding-pair,
this can become quite tiresome.

In the decoding/encoding example, we wrote a field that could be used to parse IPv4 addresses. Instead of repeating
ourselves when we need to do this multiple times, we could also create an entirely new ``IPAddressField``, setting the
default for the :attr:`IntegerField.length` and changing the return value of the field::

    import ipaddress

    class IPAddressField(IntegerField):
        def __init__(self, *args, length=4, signed=False, **kwargs):
            super().__init__(*args, length=length, signed=signed, **kwargs)

        def from_stream(self, stream, context):
            value, length = super().from_stream(stream, context)
            return ipaddress.IPv4Address(value), length

        def to_stream(self, stream, value, context):
            return super().to_stream(stream, int(value), context)

Note how we have ordered the ``super()`` calls here: we want to read from the stream and then
adjust the value, but we need to adjust the value before we are writing it to the stream.

Overriding :meth:`Field.from_stream` and :meth:`Field.to_stream` using Python inheritance is a common occurrence.
Although the example above is very simple, you could adjust how the field works and acts entirely. For instance, the
:class:`BitField` is a subclass of :class:`ByteField`, though it works on bits rather than bytes.

Note that there are many more functions you can override. The above example is a valid use-case, though overriding
:meth:`Field.decode_value` and :meth:`Field.encode_value` might have been more appropriate. See :ref:`ValueParsing` for
an overview of the methods where a value passes through to see where your use-case fits best. Also remember to read the
documentation for :class:`Field` to see what callbacks are used for what.

Writing your own field
======================
The most complex method of changing how parsing works is by implementing your own field. You do this by inheriting from
:class:`Field` and implementing :meth:`Field.from_stream` and :meth:`Field.to_stream`. You then have full control over
the stream cursor, how it reads values and how it returns those.

In this example, we'll be implementing
`variable-length quantities <https://en.wikipedia.org/wiki/Variable-length_quantity>`_. Since this field has a
variable-length (what's in a name) and parsing is entirely different from another field, we have to implement a new
field.

.. hint::

   A field implementing `variable-length quantities <https://en.wikipedia.org/wiki/Variable-length_quantity>`_ is
   already in Destructify: :class:`VariableLengthIntegerField`. You do not have to implement it yourself -- this
   merely serves as an example.

The following code could be used to implement such a field::

    class VariableLengthIntegerField(Field):
        def from_stream(self, stream, context):
            result = count = 0
            while True:
                count += 1
                c = stream.read(1)[0]  # TODO: verify that 1 byte is read
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
            return stream.write(bytes(result))

Though actually parsing the field may seem like a complicated beast, the actual parsing is quite easy: you define
how the field is read/written and you are done. When writing a field, you must always take care of the following:

* You must add in some checks to verify that everything is as you'd expect. In the above example, we have omitted these
  checks for brevity, but added a comment where you still need to add some checks, for instance, verify that we have
  not reached the end of the stream in :meth:`Field.from_stream` and raise a :exc:`StreamExhaustedError`.

* You must ensure that the stream cursor is at the end of the field when you are done reading and writing. This is the
  place where the next field continues off. This is typically true, but if you need to look-ahead this may be an
  important gotcha.

There is more to implementing a field, as the next chapters will show you, though the basics will always remain the
same. Read the full Python API for :class:`Field` to see which callbacks are available.

Supporting length
=================
You may have noticed that you can do ``len(Structure)`` on a structure and -- if possible -- get the byte length of
the structure. This is actually implemented by calling ``len(field)`` on all fields in the structure. The default
implementation of :class:`Field` is to raise an :exc:`ImpossibleToCalculateLengthError`, so that when a field does not
specify its length, the :class:`Structure` that called will raise the same error.

Therefore, you are encouraged to add a ``__len__`` method to your fields when you can tell the length of a field
beforehand (i.e. without a context)::

    class AlwaysFourBytesField(Field):
        def __len__(self):
            return 4

Note that you must return either a positive integer or raise an error. If your field depends on another field to
determine its length, you should raise an error: you can only implement this field if you know its value regardless
of the parsing state.

Supporting lazy read
====================
The attribute :attr:`Field.lazy` controls how a field is read from the stream: if it is :const:`True`, the field is not
actually read during parsing, but only on its first access. This requires the field to know how much it needs to skip
to find the start of the next field. This is implemented by :meth:`Field.seek_end`, which is only called in the case
that the start of the next field must be calculated (this is not the case e.g. if the next field has an absolute
offset).

The default implementation is to check whether ``len(field)`` returns a usable result, and skips this amount of bytes.
If the result is not usable, :const:`None` is returned, and the field is read regardless of the :attr:`Field.lazy`
setting.

However, there are cases where we can simply read a little bit of data to determine the length of the field, and then
skip over the remainder of the field without parsing the entire field. This can be implemented by writing your own
:meth:`Field.seek_end`, which is more efficient than reading the entire field.

For instance, say that we have want to implement how UTF-8 encodes its length: if the first byte starts with ``0b0``,
it is a single byte-value, if the first byte starts with ``0b110``, it is a two-byte value, ``0b1110`` a three-byte
value and so forth. You could write a field like this::

    class UTF8CharacterField(destructify.Field):
        def _get_length_from_first_byte(self, value):
            val = ord(value)
            for length, start_bits in enumerate(0b0, 0b110, 0b1110, 0b11110, 0b111110, 0b1111110):
                if val >> ((8 - start_bits.bit_length()) if start_bits else 7) == start_bits:
                    return length
            raise ParseError("Invalid start byte.")

        def seek_end(self, stream, context, offset):
            read = stream.read(1)
            if len(read) != 1:
                raise StreamExhaustedError()
            return stream.seek(self._get_length_from_first_byte(read) - 1, io.SEEK_CUR)

        def from_stream(self, stream, context):
            # left as an exercise to the reader

        def to_stream(self, stream, context):
            # left as an exercise to the reader

This still reads the first byte of the structure, but does not need to parse the entire structure.

Testing your field
==================
Now, the only thing left is writing unittests for this. Since this field is mostly simple idempotent, we can use these
simple tests to verify it all works according to plan, You may notice that the only simple idempotency exception is
that values may be repended with ``80`` bytes as that does not change its value::

    class VariableLengthIntegerFieldTest(DestructifyTestCase):
        def test_basic(self):
            self.assertFieldStreamEqual(b'\x00', 0x00, VariableLengthIntegerField())
            self.assertFieldStreamEqual(b'\x7f', 0x7f, VariableLengthIntegerField())
            self.assertFieldStreamEqual(b'\x81\x00', 0x80, VariableLengthIntegerField())
            self.assertFieldFromStreamEqual(b'\x80\x80\x7f', 0x7f, VariableLengthIntegerField())

        def test_negative_value(self):
            with self.assertRaises(OverflowError):
                self.call_field_to_stream(VariableLengthIntegerField(), -1)

        def test_stream_not_sufficient(self):
            with self.assertRaises(StreamExhaustedError):
                self.call_field_from_stream(VariableLengthIntegerField(), b'\x81\x80\x80')
