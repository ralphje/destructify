==========
Structures
==========
.. module:: destructify

Destructify uses structures to define how to parse binary data structures. If you have used Django before,
you may see some resemblance with how models are defined in that project. Don't worry if you don't know anything about
Django, as the following is everything you need to know:

* Each structure is a Python class that subclasses :class:`Structure`
* Each attribute of the structure defines a field in the binary structure

All of this allows you to write a very clean looking specification of binary data structures that is easy to write, but
also trivial to read and comprehend. Some of this even resembles parts of C-style structures, so it can be dead simple
to write some code to interface between C programs and Python programs.

Simple example
==============
Let's say we have some simple C-style structure that allows you to write your name (in a fixed-length fashion), your
birth year and your balance with some company (ignoring the cents). This might look like the following in C:

.. code-block:: C

   struct {
       char name[24];
       uint16_t birth_year;
       int32_t balance;
   } Person;

In Destructify, you would specify this as follows::

   import destructify

   class Person(destructify.Structure):
       name = destructify.StringField(length=5, encoding='utf-8')
       birth_year = destructify.IntegerField(length=2, signed=False)
       balance = destructify.IntegerField(length=4, signed=True)

       class Meta:
           byte_order = 'big'

Each of the attributes above are called fields. Each field is specified as a class attribute, and each attribute
defines how it parses this part of the structure. Also note that ordering matters, and fields are parsed in the order
they are defined in.

You may also have noticed that we have defined a :class:`Meta` inner class containing the :attr:`Meta.byte_order`
attribute. This is required for the two :class:`IntegerField` we use. When writing binary data, the byte order, or
`endianness <https://en.wikipedia.org/wiki/Endianness>`_ as it is also commonly called, specifies how bytes are read and
written. You can specify this as a default on a per-structure basis or specifically on a per-field basis.

You can now start using this structure. Reading a structure is as easy as calling the class-method
:meth:`Structure.from_bytes` as follows::

    >>> person = Person.from_bytes(b"Bobby\x07\xda\x00\x00\x00\xc8")
    <Person: Person(name='Bobby', birth_year=2010, balance=200)>

From the resulting object, you can simply access the different attributes::

    >>> person.name
    Bobby
    >>> person.birth_year
    2010

Creating a structure is also very simple, as you can pass all attributes to the constructor of the structure, or change
their value as attribute. Obtaining the binary structure is then as easy as converting the object to :class:`bytes`::

    >>> Person(name="Carly", birth_year=1993, balance=-100)
    >>> person.name = "Alice"
    >>> bytes(person)
    b"Alice\x07\xc9\xff\xff\xff\x9c"


C-style operations
==================
Continuing our above example of a C-style struct, we know that we can also obtain the size of a structure in C using the
``sizeof`` function. We can do the same in Destructify using ``len``::

    >>> len(Person)
    11

This is only possible when we use fixed-length fields. If we have some field somewhere that is of variable length, we
can't determine this length anymore::

    >>> class FlexibleStructure(destructify.Structure):
    ...     field = destructify.StringField(terminator=b'\0')
    ...
    >>> len(FlexibleStructure)
    Traceback (most recent call last):
        (...)
    destructify.exceptions.ImpossibleToCalculateLengthError

Similarly, you can use :meth:`Structure.as_cstruct` to see how you'd write the same structure in a C-style struct. Note
that

Field types
===========
In the first example, we have shown some field types, but Destructify comes with dozens of different built-in fields.
Each of these is used to define how a piece of bytes is to be interpreted and how it is to be written to bytes again.

It is not possible to make a general assumption about all fields, but most fields combine different methods of consuming
and writing data to and from a stream, with a single Python representation. Taking the :class:`StringField` as an
example, you may have noticed that we are only able to fit 5-byte names in this field. What if we had longer or shorter
names? Luckily, :class:`StringField` allows you to pass different keyword-arguments to define how this works.

Reading through :ref:`FieldSpec` you will discover that all fields have a smorgasbord of different attributes to control
how they read, convert and parse values to and from a stream. To illustrate what we mean, we show you how
:class:`BytesField` has different operating modes in the next section.

But remember, you can always implement your own field if none of the built-in fields does what you want.

Controlling a field through attributes
======================================
Most fields take the :class:`BytesField` as a base class, as this field has various common options for parsing bytes
from a stream. Two of the most common cases, a fixed-length field, and a field 'until' some byte sequence, are possible.
It is even possible to make this a lot more complex, as we try to show in five examples:

``BytesField(length=5)``
  This reads exactly the specified amount of bytes from the field, and returns that immediately.

``BytesField(length=20, padding=b' ')``
  This is a variant of the previous example, that allows for some variance in the field: 20 bytes are read and all
  spaces are removed from right-to-left. When writing, spaces are automatically added as well.

``BytesField(terminator=b'\0')``
  This form allows us to read until a single NULL-byte is encountered. This is typically how strings are represented in
  C, and are called NULL-terminated strings. The advantage of this is that the value can take any length, as long as it
  is terminated with a NULL-byte (and the value itself does not contain any NULL-bytes).

  Using this has some disadvantages, as it is not possible to use :attr:`Field.lazy` on such a field: it must be parsed
  in its entirety to know its length.

``BytesField(length=20, terminator=b'\0')``
  This form combines the two methods by specifying both a fixed amount of bytes, *and* a terminator. This is a common
  model when writing strings to fixed-length buffers in C: it reads 20 bytes from the stream, and then looks for the
  terminator.

  This is different from specifying a length with padding, as this allows junk to exist in the padding of the field.
  That may occur commonly in C: imagine you declare a buffer of fixed length, but do not properly fill it with zeroes.
  In that case, some random bytes may exist in the padding, not just NULL-bytes.

  Note that this field does not know how to write a value that is too short, as padding has nog been defined yet; but
  there is a solution:

``BytesField(length=20, terminator=b'\0', padding=b'\0')``
  This is the best of all worlds, allowing us to read 20 bytes, terminate the relevant part at the NULL-terminator while
  reading, and allow us to write shorter-length values as these will be padded with NULL-bytes. This is usually how
  you'd implement fixed-length C-style strings.

As you can see from these five examples, it highly depends on how your structure looks like what you'd define in the
structure. Again, these are only examples, and you should read :ref:`FieldSpec` to get an idea of all of the options
for all of the built-in fields.

Streams
=======
Until now, you may have noticed we have been using :meth:`Structure.from_bytes` and :meth:`Structure.to_bytes` to
convert from and to bytes. In fact, these are convenience methods, as Destructify actually works on streams. You can
use this to simply open a file and parse this, without needing to convert it to bytes first::

    with open("file.png", "rb") as f:
        structure = MyStructure.from_stream(f)

This allows you to read in large files into a Python structure.

Structure methods
=================
Apart from the way we define the fields in a structure, all structures are normal Python classes and can
add additional functions and calculated properties. This is helpful, as you can use this to create per-instance
methods that allow you to work on a particular instance of your structure, and keep your business logic in one place::

    class Person(destructify.Structure):
       name = destructify.StringField(length=5, encoding='utf-8')
       birth_year = destructify.IntegerField(length=2, signed=False)
       balance = destructify.IntegerField(length=4, signed=True)

       class Meta:
           byte_order = 'big'

       def add_to_balance(self, amount):
           """Adds the given amount to the balance of this person."""
           self.balance += amount

       @property
       def age(self):
           """The most naive method of determining the age of the person."""
           import datetime
           return datetime.date.today().year - self.birth_year

Note that we have implemented the last method in this example as a property, showing how you would implement a
calculated property that is not written to the binary structure.

The :class:`Structure` defines some function of its own, for instance the :meth:`Structure.to_stream` method. You're
free to override these functions to do whatever you like. An example would be::

    class Person(destructify.Structure):
       ...

       def to_stream(self, *args, **kwargs):
           do_something()
           result = super().to_stream(*args, **kwargs)
           do_more()
           return result

In this example, we do something just before we write the data to a stream. It's important to call the superclass
method if you want to retain original behaviour and return its value (that's what that ``super()`` call is for). Also
note that we pass the original arguments of the function through to the original function, without defining what these
are precisely.

As it is common to modify some fields just before they have been written, you may also choose to override
:class:`Structure.finalize`.

The Meta class
==============
You may have noticed that we use a class named :class:`Structure.Meta` in some of our definitions. You can use this
class to specify some global attributes for your structure. For instance, this allows you to set some defaults on
some fields, e.g. the :attr:`StructureOptions.byte_order`.

The Meta attributes you define, are available in the :attr:`Structure._meta` attribute of the structure. This is a
:class:`StructureOptions` object.

The following options are available:

.. attribute:: StructureOptions.structure_name

   The name of the structure. Defaults to the class name of the structure.

.. attribute:: StructureOptions.byte_order

   The default byte-order for fields in this structure. Is not set by default, and can be ``little`` or ``big``.

.. attribute:: StructureOptions.encoding

   The default character encoding for fields in this structure. Defaults to ``utf-8``.

.. attribute:: StructureOptions.alignment

   Can be set to a number to align the start of all fields. For instance, if this is ``4``, the start of all fields
   will be aligned to 4-byte multiples; meaning that, after a 2-byte field, a 2-byte gap will automatically be added.
   This is useful for e.g. C-style structs, that are automatically aligned.

   This alignment does *not* apply when :attr:`Field.offset` or :attr:`Field.skip` is set. When using subsequent
   :class:`BitField` s, this may also be ignored.

   .. seealso::

      `The Lost Art of Structure Packing <http://www.catb.org/esr/structure-packing/>`_
         Some background information about alignment of C-style structures.

.. attribute:: StructureOptions.checks

   This is a list of checks to execute after parsing the :class:`Structure`, or just before writing it. Every check
   must be a function that accepts a :attr:`ParsingContext.f` object, and return a truthy value when the check is
   successful. For instance::

       class Struct(Structure):
           value = IntegerField(length=1)
           checksum = IntegerField(length=1)

           class Meta:
               checks = [
                   lambda f: (f.value1 * 2 % 256) == f.checksum
               ]

   When any of the checks fails, a :exc:`CheckError` is raised.

.. attribute:: StructureOptions.capture_raw

   If True, requests the :class:`ParsingContext` to capture raw bytes for all fields in the structure. This will add a
   stream wrapper when data is read or written from this structure, to prevent the stream from having to be read twice.

.. attribute:: StructureOptions.length

   Defines the length of the structure. This can be useful if the length of your structure cannot be calculated (e.g.
   when the length of two fields is dynamic, but always sums up to be the same) or if you want to limit unbounded reads
   in some fields.

   This option will affect ``len(Structure)`` as well as all parsing and writing operations. When used in
   conjunction with :attr:`StructureField.length`, both are applied, i.e. the shortest one will prevail.

   Note that specifying a too short length will result in :exc:`StreamExhaustedError` exceptions.
