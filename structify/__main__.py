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
    length = structify.UnsignedByteField(default=0)
    data = structify.FixedLengthField(length='length')


two = TestStructure2.from_bytes(b'\x01ABC')
print(two.length)
print(two.data)
two.length = None
two.data = b"asdfasdfasdf"
print(two.to_bytes())


class SubStructure(structify.Structure):
    length = structify.UnsignedByteField(default=1)
    numbers = structify.ArrayField(structify.FixedLengthField(length=lambda s: s.length), size='length')

example = SubStructure.from_bytes(b"\x02\x01\x02\x01\x02")
print(example.numbers)
example = SubStructure.from_bytes(b"\x01\x01")
print(example.numbers)


class EncapsulatingStructure(structify.Structure):
    structs = structify.ArrayField(structify.StructureField(SubStructure), size=2)

example = EncapsulatingStructure.from_bytes(b"\x02\x01\x02\x01\x02\x01\x01")
print(example.structs[0].numbers, example.structs[1].numbers)


class ZeroTerminatedStructure(structify.Structure):
    zf = structify.TerminatedField()

example = ZeroTerminatedStructure.from_bytes(b"asdfasdfasdf\x00")
print(example.zf)

