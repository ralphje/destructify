Destructify
===========

Destructify is a Pythonic and pure-Python 3 method to express binary data, allowing you to read and write binary
structures. You simply specify a structure by creating a class as follows::

    class ExampleStructure(destructify.Structure):
        some_number = destructify.BEIntegerField()
        length = destructify.UnsignedByteField(default=0, override=lambda s, v: len(s.data))
        data = destructify.FixedLengthField(length='length')

Now you can parse your own binary data::

    example = ExampleStructure.from_bytes(b"\x01\x02\x03\x04\x0BHello world")
    print(example.data)  # b'Hello world'

Or write your own data::

    example2 = ExampleStructure(data=b'How are you doing?')
    print(bytes(example2))  # b'\x00\x00\x00\x00\x12How are you doing?'

