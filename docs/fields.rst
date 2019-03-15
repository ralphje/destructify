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

For instance, when we consider a :class:`VariableLengthIntegerField`, the byte
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

Subclassing an existing field
=============================
If you only need to change a field a little bit, you may be best off subclassing an existing field and changing how
it behaves. Say, for instance, we have a field that follows normal parsing rules for bytes, but requires us to read
the result from back-to-front. We could simply subclass :class:`BytesField` and change this::

    class ReversedBytesField(BytesField):
        def from_stream(self, stream, context):
            value, length = super().from_stream(stream, context)
            return value[::-1], length
        def to_stream(self, stream, value, context):
            return super().to_stream(stream, value[::-1], context)

Note that the order of how we position the ``super()``-calls matters here: we want to read from the stream and then
adjust the value, but we need to adjust the value before we are writing it to the stream. Another example of
subclassing :class:`IntegerField` to return an IPAddress object instead, we should have done this::

    import ipaddress
    class IPAddressField(IntegerField):
        def __init__(self, *args, length=4, signed=False, **kwargs):
            super().__init__(*args, length=length, signed=signed, **kwargs)
        def from_stream(self, stream, context):
            value, length = super().from_stream(stream, context)
            return  ipaddress.IPAddress(value), length
        def to_stream(self, stream, value, context):
            return super().to_stream(stream, int(value), context)

You can similarly extend the behaviour of any other existing class using standard Python inheritance.

Writing your own field
======================
However, what
if none of the fields does what you want? Then you have to create a class inheriting from :class:`Field` and override
:meth:`Field.from_stream` and :meth:`Field.to_stream`.

Take, for instance, `variable-length quantities <https://en.wikipedia.org/wiki/Variable-length_quantity>`_. Since this
had to be written for this documentation anyway, it is included in Destuctify, but assume we hadn't. Then you'd write
it as follows::

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

As you can see, this is not that hard! We have omitted some additional checks from this example, such as that we
have actually read 1 byte (and should raise :exc:`StreamExhaustedError` if it isn't) and verify that the value is
positive when writing, but other than that, this field should work. (Check the source code of Destructify to verify how
the field is actually implemented).

In this case it is easily accomplished, but you must always make sure that the stream cursor is at the correct position
after the :meth:`Field.to_stream` and :meth:`Field.from_stream` methods are done. Typically, this will hold::

    tell_before = stream.tell()
    result = Field.to_stream(stream, ...)   # similar for from_stream
    tell_before + result == stream.tell()

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

Supporting length
=================
::

    class DemoField(Field):
        def __len__(self):
            return 4

Supporting lazy read
====================
The example we have chosen to show in this documentation, is impossible to read lazily, as the entire field must be
parsed before the length is known. But, what if we know the length of our field? Then we can support lazy read as
follows::

    class OurField(Field):
        def seek_end(self, stream, context, offset)
            return stream.seek(4, io.SEEK_CUR)
