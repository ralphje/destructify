import structify


# TEMPORARY TESTING CLASS

class TestStructure(structify.Structure):
    field = structify.BEShortField()
    field2 = structify.LEShortField(default=lambda s: s.field)


t = TestStructure.from_bytes(b"0123")
print(t.field)
print(t.field2)
print(repr(b"0123"), repr(t.to_bytes()))

t2 = TestStructure(field=12)
print(t2.field)
print(t2.field2)
print(t2.to_bytes())


class TestStructure2(structify.Structure):
    length = structify.UnsignedByteField(default=0, prepper=lambda s, v: len(s.data))
    data = structify.FixedLengthField(length='length')


two = TestStructure2.from_bytes(b'\x01ABC')
print(two.length)
print(two.data)
two.data = b"asdfasdfasdf"
print(two.to_bytes())
