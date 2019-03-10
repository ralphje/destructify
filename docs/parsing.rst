================
Advanced parsing
================
In the previous chapter, we have covered generally how you'd define a simple structure.
However, there is much more ground to cover there, so we'll take a deeper dive into how parsing works in Destructify.

Depending on other fields
=========================
Until now, we have been using fixed length fields, without any dependency on other fields. However, it is not untypical
for a field to have its length set by some other property. Take the following example::

    import destructify

    class DependingStructure(destructify.Structure):
        length = destructify.IntegerField(1)
        content = destructify.BytesField(length='length')

Since the :attr:`BytesField.length` attribute is special and allows you to set a string referencing another field,
you can now simply do the following::

    >>> DependingStructure(content=b"hello world").to_bytes()
    b'\x0bhello world'
    >>> DependingStructure.from_bytes(b'\x06hello!')
    <DependingStructure: DependingStructure(length=6, content=b'hello!')>

Actually, there's some magic involved here, and that centers around the :class:`ParsingContext` class. This class is
passed around while parsing from and writing to a stream, and filled with information about the current process. This
allows you to reference fields that have been parsed before the current field. This is what happens when you pass a
string to the :attr:`BytesField.length` attribute: it is interpreted as a field name and obtained from the context
while parsing and writing the data.

Calculating attributes
======================
The :attr:`BytesField.length` attribute actually allows you to provide a callable as well. This callable takes a single
argument, which is a :attr:`ParsingContext.f` object. This is a special object that allows you to transparently access
other fields during parsing. This allows you to write more advanced calculations if you need to, or add multiple fields
together::

    class DoubleLengthStructure(destructify.Structure):
        length1 = destructify.IntegerField(1)  # multiples of 10 (for some reason)
        length2 = destructify.IntegerField(1)
        content = destructify.BytesField(length=lambda c: c.length1 * 10 + c.length2)

.. class:: this

As ``lambda`` functions can become quite tiresome to write out, it is also possible to use the special :class:`this`
object to write this. The :class:`this` object is a higher-level lazily parsed object that constructs ``lambda``
functions for you. This is better shown by example, as these are equivalent::

    this.field + this.field2 * 3
    lambda this: this.field + this.field2 * 3

Writing the same structure again, we could also do the following::

    import destructify
    from destructify import this

    class DoubleLengthStructure(destructify.Structure):
        length1 = destructify.IntegerField(1)
        length2 = destructify.IntegerField(1)
        content = destructify.BytesField(length=this.length1 * 10 + this.length2)

Note that this lazy object can do most normal arithmetic, but unfortunately, Python does not allow us to override the
``len`` function to return a lazy object. Therefore, you can use ``len_`` as a lazy alternative.

Overriding values
=================
Having shown how we can read values without much problem, being able to write values is also quite important for
structures. We know from previous examples that this works without much issues::

    >>> DependingStructure(content=b"hello world").to_bytes()
    b'\x0bhello world'

That begs the question: how does ``length`` know that it know that it needs to get the length from the ``content``
field? That is because there's something else going on in the background: when set to a string, the :attr:`BytesField`
automatically specifies the :attr:`Field.override` of the ``length`` field to be set to another value, just before it
is being written.

This is nice and all, but what if the length is actually some calculation that is more advanced than simply taking the
length? For instance, what if the length field includes its own length? This is also very easy! ::

    import destructify

    class DependingStructure(destructify.Structure):
        length = destructify.IntegerField(length=4, byte_order='big', signed=False,
                                          override=lambda c, v: len(c.content) + 4 if v is None else v)
        content = destructify.BytesField(length=lambda c: c.length - 4)

As you can spot, we now explicitly state using lambda functions how to get the length when we are reading the field,
and also how to set the length when we are writing the field.

As with the :attr:`BytesField.length` we defined before, the :attr:`Field.override` we have specified, receives a
:attr:`ParsingContext.f`, but also the current value. We have added in a check to not override the value of
``length`` when it is already set to something else, allowing us to explicitly write 'wrong' values if we need to.

Several fields allow you to specify advanced structures such as these, allowing you to dynamically modify how your
structure is built. See :ref:`FieldSpec` for a full listing of all the fields and how you can specify calculated
values.

Offset, skip and alignment
==========================
It can happen that information in your structure is scattered throughout the stream. For instance, it can happen that
a header specifies where to find the data in the stream. You can use :attr:`Field.offset` to specify an absolute offset
in the stream, given an integer or a field value::

    >>> class OffsetStructure(destructify.Structure):
    ...    offset = destructify.IntegerField(length=4, byte_order='big', signed=False)
    ...    length = destructify.IntegerField(length=4, byte_order='big', signed=False)
    ...    content = destructify.BytesField(offset='offset', length='length')
    ...
    >>> OffsetStructure.from_bytes(b'\0\0\0\x10\0\0\0\x05paddingxhello')
    <OffsetStructure: OffsetStructure(offset=16, length=5, content=b'hello')>
If you need to specify a offset from the end of the stream, a negative value is also possible. During writing, this is
a little bit ambiguous, so you must be careful how you'd define this.

Remember that fields are always parsed in their defined order, and a field that follows a offset field, will continue
parsing where the previous field left off.

If you need to skip a few bytes from the previous field, you can use :attr:`Field.skip`. You can use this to skip some
padding without defining a field specifically to parse the padding. This is something that happens commonly when the
stream is aligned to some multibyte offset, which can also be defined globally for the structure::

    >>> class AlignedStructure(destructify.Structure):
    ...     field1 = destructify.IntegerField(length=1)
    ...     field2 = destructify.IntegerField(length=1)
    ...
    ...     class Meta:
    ...         alignment = 4
    ...
    >>> AlignedStructure.from_bytes(b"\x01pad\x02pad")
    <AlignedStructure: AlignedStructure(field1=1, field2=2)>

Lazily parsing fields
=====================
It can happen that you have a structure that reads huge chunks of data from the stream, but you don't want to keep all
of this in memory while you are parsing from the stream. You can make fields lazy to defer their parsing
to a later point in time.

To support this, Destructify uses a Proxy object, that is returned by the parser instead of
the actual resulting value. This Proxy object can be used as you'd normally use the value, but it is only resolved from
the stream as soon as it is actually required. For instance::

    >>> class LazyStructure(destructify.Structure):
    ...    huge_content = destructify.BytesField(length=200, lazy=True)
    ...
    >>> l = LazyStructure.from_bytes(b"a"*200)
    >>> type(l.huge_content)
    <class 'Proxy'>
    >>> print(l.huge_content)
    b'aaaa...aaaa'

We can even show you that we only read once from the stream::

    >>> class PrintIO(io.BytesIO):
    ...     def read(self, size=-1):
    ...         print("Reading {} bytes from offset {}".format(size, self.tell()))
    ...         return super().read(size)
    ...
    >>> l = LazyStructure.from_stream(PrintIO(b"a"*200))[0]
    >>> print(l.huge_content)
    Reading 200 bytes from offset 0
    b'aaaa...aaaa'
    >>> print(l.huge_content)
    b'aaaa...aaaa'

Not all fields can be parsed lazily. For instance, a NULL-terminated :class:`BytesField` must be parsed in its entirety
before it knows its length. We need to know the field length if the field is followed by another field, so we must then
still parse the field. In this case, the laziness of the field is ignored. To show this in action, see this example::

    >>> class LazyLazyStructure(destructify.Structure):
    ...    field1 = destructify.BytesField(terminator=b'\0', lazy=True)
    ...    field2 = destructify.BytesField(terminator=b'\0', lazy=True)
    ...
    >>> s = LazyLazyStructure.from_bytes(b"a\0b\0")
    >>> type(s.field1), type(s.field2)
    (<class 'bytes'>, <class 'Proxy'>)

Since the length of ``field1`` is required for parsing ``field2``, we parse it regardless of the request to lazily parse
it.

Combining offset with lazy
==========================
There is some important synergy between fields that have a offset set to an integer (i.e. do no depend on another field)
and are lazy: this allows the field to be referenced during parsing, even if it is defined out-of-order::

    >>> class SynergyStructure(destructify.Structure):
    ...    content = destructify.BytesField(length='length')
    ...    length = destructify.IntegerField(length=1, offset=-1, lazy=True)
    ...
    >>> SynergyStructure.from_bytes(b"blahblah\x04")
    <SynergyStructure: SynergyStructure(content=b'blah', length=4)>

This works because all lazy fields with lazy offsets are pre-populated in the parsing structure, making them being able
to be referenced during parsing. In this example, the ``length`` field is referenced, therefore parsed and returned
immediately and not through a Proxy object.

This is mostly to allow you to specify a structure that is more logical, though this structure would parse the same
data::

    class LessSynergyStructure(destructify.Structure):
        length = destructify.IntegerField(length=1, offset=-1)
        content = destructify.BytesField(length='length', offset=0)
