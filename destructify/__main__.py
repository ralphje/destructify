import destructify


# TEMPORARY TESTING CLASS

class TestStructure(destructify.Structure):
    field = destructify.BEShortField()
    field2 = destructify.LEShortField(default=lambda s: s.field)


t = TestStructure.from_bytes(b"0123")
print(t.field)
print(t.field2)
print(repr(b"0123"), repr(t.to_bytes()))

t2 = TestStructure(field=12)
print(t2.field)
print(t2.field2)
print(t2.to_bytes())


class TestStructure2(destructify.Structure):
    length = destructify.UnsignedByteField(default=0)
    data = destructify.FixedLengthField(length='length')


two = TestStructure2.from_bytes(b'\x01ABC')
print(two.length)
print(two.data)
two.length = None
two.data = b"asdfasdfasdf"
print(two.to_bytes())


class SubStructure(destructify.Structure):
    length = destructify.UnsignedByteField(default=1)
    numbers = destructify.ArrayField(destructify.FixedLengthField(length=lambda s: s.length), size='length')

example = SubStructure.from_bytes(b"\x02\x01\x02\x01\x02")
print(example.numbers)
example = SubStructure.from_bytes(b"\x01\x01")
print(example.numbers)


class EncapsulatingStructure(destructify.Structure):
    structs = destructify.ArrayField(destructify.StructureField(SubStructure), size=2)

example = EncapsulatingStructure.from_bytes(b"\x02\x01\x02\x01\x02\x01\x01")
print(example.structs[0].numbers, example.structs[1].numbers)


class ZeroTerminatedStructure(destructify.Structure):
    zf = destructify.TerminatedField()

example = ZeroTerminatedStructure.from_bytes(b"asdfasdfasdf\x00")
print(example.zf)

