==========
Python API
==========
.. module:: destructify

Structure
=========
.. autoclass:: Structure

   You use :class:`Structure` as the base class for the definition of your structures. It is a class with a metaclass
   of :class:`StructureBase` that enables the fields to be parsed separately.

   .. describe:: len(Structure)

      This is a class method that allows you to retrieve the size of the structure, if possible.

   .. automethod:: Structure.from_stream

   .. automethod:: Structure.from_bytes

   .. automethod:: Structure.initialize

   .. automethod:: Structure.to_stream

   .. automethod:: Structure.to_bytes

   .. automethod:: Structure.finalize

   .. automethod:: Structure.__bytes__

   .. automethod:: Structure.as_cstruct

   .. attribute:: Structure._meta

      This allows you to access the :class:`StructureOptions` class of this :class:`Structure`.

Field
=====
.. autoclass:: Field

   .. autoattribute:: Field.ctype

   A :class:`Field` also defines the following methods:

   .. describe:: len(field)

      You can call ``len`` on a field to retrieve its byte length. It can either return a value that makes sense, or it
      will raise an :exc:`ImpossibleToCalculateLengthError` when the length depends on something that is not known yet.

   .. automethod:: Field.initialize

   .. automethod:: Field.get_initial_value

   .. automethod:: Field.get_final_value

   .. automethod:: Field.seek_start

   .. automethod:: Field.seek_end

   .. automethod:: Field.from_stream

   .. automethod:: Field.to_stream

ParsingContext
==============

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
