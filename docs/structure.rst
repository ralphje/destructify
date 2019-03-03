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

We dive deeper into the different ways :class:`StringField` operates in the section :ref:`StringFieldExample`.
A full specification of built-in fields can be found in :ref:`FieldSpec`. If none of these fields does exactly what you
need, you may consider extending one of the built-in fields, or even implementing your own.

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

All of this does not entirely explain why writing works, as how does the ``length`` field know that it needs to get the
length from the ``content`` field? That is because there's something else going on in the background: when set to a
string, the :attr:`BytesField` automatically specifies the :attr:`Field.override` of the ``length`` field to be set to
another value, just before it is being written.

This is nice and all, but what if the length is actually some calculation that is more advanced than simply taking the
length? For instance, what if the length field includes its own length? This is also very easy! ::

    import destructify

    class DependingStructure(destructify.Structure):
        length = destructify.IntegerField(length=4, byte_order='big', signed=False,
                                          override=lambda c, v: len(c.content) + 4 if v is None else v)
        content = destructify.BytesField(length=lambda c: c.length - 4)

As you can spot, we now explicitly state using lambda functions how to get the length when we are reading the field,
and also how to set the length when we are writing the field.

The :attr:`Field.override` we specify, receives the
current :attr:`ParsingContext.f` and the current value. Using attribute access on the  :attr:`ParsingContext.f`, we get the
length of the ``content`` field. We have added in a check to not override the value of
``length`` when it is already set to something else, allowing us to explicitly write 'wrong' values if we need to.

Similarly, the :attr:`BytesField.length` accepts a function taking a single argument: the :attr:`ParsingContext.f`. A
simple attribute access allows us to get the current value of the just-before parsed ``length`` field.

Several fields allow you to specify advanced structures such as these, allowing you to dynamically modify how your
structure is built. See :ref:`FieldSpec` for a full listing of all the fields and how you can specify calculated
values.

The S object
------------

.. class:: S

There is one final thing we want to show you: using the special :class:`S` object to construct lambda functions. This
object can be used similarly to a :attr:`ParsingContext.f` object, except that it can be used to construct a lambda
automatically. This means that these are equivalent::

    S.field + S.field2 * 3
    lambda c: c.field + c.field2 * 3

The :class:`S` object can be used in any place where a single-argument lambda is expected::

    import destructify
    from destructify import S

    class DependingStructure(destructify.Structure):
        ...  # same as above
        content = destructify.BytesField(length=S.length - 4)

Note that many operations are not possible on a :class:`S` object, because they require a lazy alternative. This holds
for the ``len`` function; a lazy alternative is available in :func:`len_`.

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

.. autoclass:: StructureOptions

    The :class:`StructureOptions` class is the object that is automatically created when you create a :class:`Structure`
    and is accessible through :attr:`Structure._meta`. The information in this object is based on the data you specify
    in the class :class:`Structure.Meta` in the definition of your structure.

   .. automethod:: StructureOptions.get_field_by_name

   .. attribute:: object_name

      The name of the structure's definition class. Defaults to the name of your class.

   .. attribute:: structure_name

      The name of the structure. Defaults to the lowercased name of your class.

   .. attribute:: byte_order

      The default byte-order for fields in this structure. Is not set by default, and can be ``little`` or ``big``.

   .. attribute:: encoding

      The default character encoding for fields in this structure. Defaults to ``utf-8``.

Python API
==========
.. autoclass:: Structure

   You use :class:`Structure` as the base class for the definition of your structures.

   .. automethod:: Structure.from_stream

   .. automethod:: Structure.from_bytes

   .. automethod:: Structure.finalize

   .. automethod:: Structure.to_stream

   .. automethod:: Structure.to_bytes

   .. automethod:: Structure.__bytes__

   .. automethod:: Structure.as_cstruct

   .. attribute:: Structure._meta

      This allows you to access the :class:`StructureOptions` class of this :class:`Structure`.

.. autoclass:: StructureBase

   This is the metaclass of :class:`Structure`.

   .. automethod:: StructureBase.__len__