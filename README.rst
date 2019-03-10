===========
Destructify
===========
.. image:: https://img.shields.io/travis/com/ralphje/destructify.svg
   :target: https://travis-ci.com/ralphje/destructify?branch=master

.. image:: https://img.shields.io/codecov/c/github/ralphje/destructify.svg?style=flat
   :target: http://codecov.io/github/ralphje/destructify?branch=master

.. image:: https://img.shields.io/pypi/v/destructify.svg
   :target: https://pypi.python.org/pypi/destructify

.. image:: https://img.shields.io/readthedocs/destructify.svg
   :target: https://readthedocs.org/projects/destructify/

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

Documentation
-------------
Documentation for Destrucify is available at https://destructify.readthedocs.io/en/latest/
or in the ``docs/`` directory.

Installation
------------
Destructify is available at the Python Package Index::

    pip install destructify

Contributing
------------
Since Destructify is an open source project, contributions of many forms are welcomed. Examples of possible
contributions include:

* Bug patches
* New features
* Documentation improvements
* Bug reports and reviews of pull requests

We use GitHub to keep track of issues and pull requests. You can always
`submit an issue <https://github.com/ralphje/destructify/issues>`_ when you encounter something out of the ordinary.

