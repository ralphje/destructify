Welcome to Destructify's documentation!
=======================================

Destructify is a Pythonic and pure-Python 3 method to express binary data, allowing you to read and write binary
structures. You simply specify a structure by creating a class as follows:

.. code-block:: python

   class ExampleStructure(destructify.Structure):
       some_number = destructify.IntegerField(default=0x13, length=4, byte_order='little', signed=True)
       length = destructify.IntegerField(length=1)
       data = destructify.FixedLengthField(length='length')

Now you can parse your own binary data:

.. code-block:: python

   example = ExampleStructure.from_bytes(b"\x01\x02\x03\x04\x0BHello world")
   print(example.data)  # b'Hello world'

Or write your own data:

.. code-block:: python

   example2 = ExampleStructure(data=b'How are you doing?')
   print(bytes(example2))  # b'\x13\x00\x00\x00\x12How are you doing?'

Contents:

.. toctree::
   :maxdepth: 2

   structure
   fields
   fieldspec
   changelog



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

