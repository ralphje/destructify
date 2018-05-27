import destructify


# TEMPORARY TESTING CLASS

class TestStructure(destructify.Structure):
    field = destructify.BEShortField()
    field2 = destructify.LEShortField(default=lambda s: s.field)
    field3 = destructify.ShortField(default=lambda s: s.field)

    class Meta:
        byte_order = 'little'


t = TestStructure.from_bytes(b"\x00\x01\x01\x00\x00\x01")
print(t.field)
print(t.field2)
print(t.field3)

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

print(SubStructure.as_cstruct())
example = SubStructure.from_bytes(b"\x02\x01\x02\x01\x02")
print(example.numbers)
example = SubStructure.from_bytes(b"\x01\x01")
print(example.numbers)


class EncapsulatingStructure(destructify.Structure):
    structs = destructify.ArrayField(destructify.StructureField(SubStructure), size=2)

print(EncapsulatingStructure.as_cstruct())
example = EncapsulatingStructure.from_bytes(b"\x02\x01\x02\x01\x02\x01\x01")
print(example.structs[0].numbers, example.structs[1].numbers)


class ZeroTerminatedStructure(destructify.Structure):
    zf = destructify.TerminatedField()

example = ZeroTerminatedStructure.from_bytes(b"asdfasdfasdf\x00")
print(ZeroTerminatedStructure.as_cstruct())
print(example.zf)


class AlignedStructure(destructify.Structure):
    length = destructify.UnsignedByteField(default=1)

    class Meta:
        byte_order = 'le'


print(AlignedStructure.as_cstruct())


class ArrayStructure(destructify.Structure):
    value = destructify.ArrayField(destructify.ShortField(), size=5)

print(ArrayStructure.as_cstruct())
print(len(ArrayStructure))


class ConditionalStructure(destructify.Structure):
    condition = destructify.ByteField()
    value = destructify.ConditionalField(destructify.ShortField(), condition='condition')

print(ConditionalStructure.from_bytes(b"\0"))
print(bytes(ConditionalStructure.from_bytes(b"\0")))
print(ConditionalStructure.from_bytes(b"\x01\0\x01"))
print(bytes(ConditionalStructure.from_bytes(b"\x01\0\x01")))