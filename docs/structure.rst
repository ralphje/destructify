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

Field types
===========
In the above example, we have shown some field types, but Destructify comes with dozens of different built-in fields.
Each of these specifies a few different things:

* How to consume precisely enough bytes from a stream of bytes
* How to convert these bytes to a Python representation
* How to convert this back to a bytes representation
* How to write this back to a stream of bytes

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

Full specification of built-in fields can be found in :ref:`FieldSpec`. If none of these fields does exactly what you
need, you may consider extending one of the built-in fields, or even implementing your own.

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

TODO: as_cstruct()

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

Structure class
===============
.. autoclass:: Structure

   .. automethod:: Structure.from_stream

   .. automethod:: Structure.from_bytes

   .. automethod:: Structure.finalize

   .. automethod:: Structure.to_stream

   .. automethod:: Structure.to_bytes

   .. automethod:: Structure.__bytes__

   .. automethod:: Structure.as_cstruct

.. autoclass:: StructureBase

   .. automethod:: StructureBase.__len__
